# pylint: disable=import-error

if "bpy" in locals():
  # pylint: disable=used-before-assignment
  import importlib
  if "materials" in locals():
    importlib.reload(materials)
  if "mesh_parser" in locals():
    importlib.reload(mesh_parser)
  if "readutil" in locals():
    importlib.reload(readutil)

import bpy
import collections
import os
import math
import mathutils

from . import materials
from . import mesh_parser
from . import readutil

Options = collections.namedtuple(
    'Options',
    ['IMPORT_SKYBOX', 'IGNORE_PLACEHOLDERS', 'USE_VERTEX_COLOR_MATERIALS'])
WORLD_TRANSFORM = mathutils.Matrix.Rotation(math.radians(90.0), 4, 'X')


class AzfImportError(Exception):
  pass


class AzfParser:
  def __init__(self, options):
    self.options = options
    self.mat_manager = materials.MaterialManager(options)

  def parse_map(self, filepath):
    basename = os.path.splitext(os.path.basename(filepath))[0]
    f = readutil.BinaryFileReader(filepath)

    instance_table_header_offs = f.read_uint32()
    if instance_table_header_offs == 0 or instance_table_header_offs >= f.filesize:
      raise AzfImportError(
          f'Invalid instance sector offset {hex(instance_table_header_offs)}')

    mesh_count = (instance_table_header_offs - 0x4) // 0x4
    mesh_offs_table = f.read_nuint32(mesh_count)
    mesh_lut = [[]] * mesh_count

    f.seek(instance_table_header_offs)
    instance_count, skybox_count = f.read_nuint16(2)
    instance_table_offs = instance_table_header_offs + f.read_uint32()
    for i in range(instance_count):
      if i < skybox_count and not self.options.IMPORT_SKYBOX:
        continue
      f.seek(instance_table_offs + i * 0x40)
      mesh_index = f.read_uint16()
      f.skip(6)
      rot = [math.radians(v / 10) for v in f.read_nint16(3)]
      f.skip(2)
      pos = f.read_nfloat32(4)
      scale = f.read_nfloat32(4)

      rotation_matrix = mathutils.Euler(rot).to_matrix()
      rotation_matrix.resize_4x4()
      translation_matrix = mathutils.Matrix()
      translation_matrix[0][3] = pos[0]
      translation_matrix[1][3] = pos[1]
      translation_matrix[2][3] = pos[2]
      scale_matrix = mathutils.Matrix()
      scale_matrix[0][0] = scale[0]
      scale_matrix[1][1] = scale[1]
      scale_matrix[2][2] = scale[2]

      transform = (
          WORLD_TRANSFORM @ translation_matrix @ rotation_matrix @ scale_matrix)

      mesh_basename = f'{basename}{"-sky" if i < skybox_count else ""}'
      mesh_basename += f'_i{i if i < skybox_count else i - skybox_count}'
      mesh_basename += f'_m{mesh_index}'
      if mesh_lut[mesh_index]:
        objects = mesh_lut[mesh_index]
        for obj in objects:
          obj_new = obj.copy()
          obj_new.name = f'{mesh_basename}_' + '_'.join(obj.name.split('_')[3:])
          bpy.context.scene.collection.objects.link(obj_new)
      else:
        parser = mesh_parser.MeshParser(
            self.mat_manager,
            skip_armature_creation=True,
            skip_textureless_meshes=self.options.IGNORE_PLACEHOLDERS)
        objects, _ = mesh_lut[mesh_index], _ = parser.parse(
            f, mesh_offs_table[mesh_index], mesh_basename)

      for obj in objects:
        obj.matrix_local = transform

  def parse_textures(self, texture_paths):
    self.mat_manager.load_textures(texture_paths)


def load(context,
         filepath,
         *,
         import_skybox=False,
         ignore_placeholders=False,
         use_vertex_color_materials=False):
  options = Options(import_skybox, ignore_placeholders,
                    use_vertex_color_materials)

  azf_dirname = os.path.dirname(filepath).lower()
  azf_basename = os.path.splitext(os.path.basename(filepath))[0].lower()
  texture_files = []
  for filename in os.listdir(os.path.dirname(filepath)):
    basename, ext = os.path.splitext(filename)
    if ext.lower() not in ('.rtm', '.vtm'):
      continue
    if basename.lower() == azf_basename or basename[:2].lower() == 'wo':
      texture_files.append(os.path.join(azf_dirname, filename))

  try:
    parser = AzfParser(options)
    parser.parse_map(filepath)
    parser.parse_textures(texture_files)
  except (AzfImportError, mesh_parser.MeshImportError,
          materials.ImageImportError) as err:
    return 'CANCELLED', str(err)

  return 'FINISHED', ''