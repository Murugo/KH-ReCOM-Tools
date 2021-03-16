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
    'Options', ['IMPORT_SHADOW_MODEL', 'USE_VERTEX_COLOR_MATERIALS'])
WORLD_TRANSFORM = mathutils.Matrix.Rotation(math.radians(90.0), 4, 'X')


class ModelParser:
  def __init__(self, mat_manager, options):
    self.mat_manager = mat_manager
    self.options = options
    self.armature = None

  def parse(self, f, model_offs, model_basename):
    f.seek(model_offs + 0xC)
    # Assume that models with no textures are shadow models. This could be more
    # accurately determined by checking the render mode in at least one VIF
    # packet.
    texture_count = f.read_uint32()
    if texture_count == 0:
      if not self.options.IMPORT_SHADOW_MODEL:
        return []
      model_basename += '_shadow'

    parser = mesh_parser.MeshParser(
        self.mat_manager,
        armature=self.armature,
        skip_textureless_meshes=(not self.options.IMPORT_SHADOW_MODEL))
    objects, self.armature = parser.parse(f, model_offs, model_basename)

    for obj in objects:
      obj.parent = self.armature.armature_obj
      modifier = obj.modifiers.new(type='ARMATURE', name='Armature')
      modifier.object = self.armature.armature_obj
      obj.select_set(state=True)


class MdlParser:
  def __init__(self, options, mat_manager=None):
    self.options = options
    if mat_manager:
      self.mat_manager = mat_manager
    else:
      self.mat_manager = materials.MaterialManager(options)

  def parse_model(self, filepath):
    basename = os.path.splitext(os.path.basename(filepath))[0]
    f = readutil.BinaryFileReader(filepath)
    readutil.maybe_skip_ps4_header(f)

    model_parser = ModelParser(self.mat_manager, self.options)
    for i in range(0x100):
      f.seek(i * 4)
      model_offs = f.read_uint32()
      if not model_offs:
        break
      model_basename = '{}_{}'.format(basename, i)
      model_parser.parse(f, model_offs, model_basename)
    
    if model_parser.armature:
      return model_parser.armature.armature_obj

  def parse_textures(self, texture_paths):
    self.mat_manager.load_textures(texture_paths)


def load(context,
         filepath,
         *,
         import_shadow_model=False,
         use_vertex_color_materials=False):
  options = Options(import_shadow_model, use_vertex_color_materials)

  mdl_dirname = os.path.dirname(filepath).lower()
  mdl_basename = os.path.splitext(os.path.basename(filepath))[0].lower()
  texture_files = []
  for filename in os.listdir(os.path.dirname(filepath)):
    basename, ext = os.path.splitext(filename)
    if ext.lower() not in ('.rtm', '.vtm'):
      continue
    if basename.lower() == mdl_basename or basename[:2].lower() == 'wo':
      texture_files.append(os.path.join(mdl_dirname, filename))

  try:
    parser = MdlParser(options)
    parser.parse_model(filepath)
    parser.parse_textures(texture_files)
  except (mesh_parser.MeshImportError, materials.ImageImportError) as err:
    return 'CANCELLED', str(err)

  return 'FINISHED', ''