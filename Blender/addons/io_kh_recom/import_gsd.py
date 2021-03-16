# pylint: disable=import-error

if "bpy" in locals():
  # pylint: disable=used-before-assignment
  import importlib
  if "import_mdl" in locals():
    importlib.reload(import_mdl)
  if "materials" in locals():
    importlib.reload(materials)
  if "readutil" in locals():
    importlib.reload(readutil)

import bpy
import collections
import math
import mathutils
import os
import re

from . import import_mdl
from . import materials
from . import readutil

WORLD_TRANSFORM = mathutils.Matrix.Rotation(math.radians(90.0), 4, 'X')


class GsdImportError(Exception):
  pass


class GsdParser:
  def __init__(self, options):
    self.options = options
    self.mat_manager = materials.MaterialManager(options)

    # {Rsrc id -> [Objects]}
    self.rsrc_obj_map = dict()
    self.directory = ''
    self.fallback_directory = ''
  
  def parse(self, filepath):
    f = readutil.BinaryFileReader(filepath)
    self.directory = os.path.dirname(filepath)

    gdirname = os.path.basename(os.path.split(self.directory)[0])
    gdirnum_re = re.search('g([0-9]+).DAT', gdirname, re.IGNORECASE)
    if gdirnum_re:
      fallback_dir_num = int(gdirnum_re.group(1)) + 1100
      self.fallback_directory = os.path.join(self.directory, f'..\\..\\g014.DAT\\{fallback_dir_num}')
    
    gsd_files = readutil.read_rsrc_header(f)
    if len(gsd_files) == 0:
      raise GsdImportError('Rsrc header is empty')
    _, file_offs, _ = gsd_files[0]

    f.seek(file_offs)
    if f.read_string(4) != "@OSD":
      raise GsdImportError(f'Expected magic "@OSD" at offset {hex(file_offs)}')
    version = f.read_uint32()
    if version != 0x4:
      raise GsdImportError(f'Unexpected OSD version {version}')

    formation_offset_table = f.read_nuint32(0x20)
    for fm_offs in formation_offset_table:
      if fm_offs == 0:
        break
      f.seek(file_offs + fm_offs)
      # Read groups for category index 2 only for gimmicks (out of 4 category slots)
      f.skip(0x80)  # Skip 0x10 uint32 offsets * 2 categories
      group_offset_table = f.read_nuint32(0x10)
      for gp_offs in group_offset_table:
        if gp_offs == 0:
          break
        f.seek(file_offs + gp_offs + 0x4)
        obj_count = f.read_uint32()
        obj_table_offset = file_offs + f.read_uint32()
        self.parse_object_group(f, obj_table_offset, obj_count)

  def parse_object_group(self, f, obj_table_offset, obj_count):
    f.seek(obj_table_offset)
    for _ in range(obj_count):
      position = f.read_nfloat32(3)
      position = (position[0], position[1] + f.read_float32(), position[2])
      rotation_euler = [0.0, math.radians(f.read_float32()), 0.0]
      rsrc_type = f.read_uint16()
      rsrc_id = f.read_uint16()
      flags = f.read_uint32()
      f.skip(8)
      unique_id = f.read_uint32()
      if (flags & 0x2) > 0:
        rotation_euler[0] = math.radians(f.read_float32())
        rotation_euler[2] = math.radians(f.read_float32())

      # Transform object in world space.
      rotation_matrix = mathutils.Euler(rotation_euler).to_matrix()
      rotation_matrix.resize_4x4()
      translation_matrix = mathutils.Matrix()
      translation_matrix[0][3] = position[0]
      translation_matrix[1][3] = position[1]
      translation_matrix[2][3] = position[2]
      transform = (
          WORLD_TRANSFORM @ translation_matrix @ rotation_matrix)
      
      # position, rotation_euler, _ = transform.decompose()
      # bpy.ops.mesh.primitive_cube_add(location=new_loc,rotation=new_rot.to_euler())
      # bpy.context.scene.objects[-1].name = f'Gimmick_{rsrc_id}_{unique_id}'

      objects = []
      if rsrc_id not in self.rsrc_obj_map:
        print(f'*** {rsrc_id}')
        armature_obj = self.load_gimmick_objects(rsrc_id)
        if armature_obj:
          objects = [armature_obj] + [child for child in armature_obj.children]
        self.rsrc_obj_map[rsrc_id] = objects
      else:
        base_objects = self.rsrc_obj_map[rsrc_id]
        for i, obj in enumerate(base_objects):
          obj_new = obj.copy()
          obj_new.name = obj.name[:obj.name.rfind('_')]
          bpy.context.scene.collection.objects.link(obj_new)
          objects.append(obj_new)
          if i > 0:
            # Parent to new armature
            # TODO: Objects lose their pose ability after this?
            obj_new.parent = objects[0]
      
      for obj in objects:
        obj.name += f'_{unique_id}'
        if obj.type == 'ARMATURE':
          obj.matrix_local = transform

  def load_gimmick_objects(self, rsrc_id):
    gm_filename = f'GM{rsrc_id:04d}.mdl'
    filepath = os.path.join(self.directory, gm_filename)
    if not os.path.exists(filepath):
      # Fall back to secondary directory (only works when importing straight from extracted path).
      found = False
      if self.fallback_directory:
        filepath = os.path.join(self.fallback_directory, gm_filename)
        found = os.path.exists(filepath)
      if not found:
        # TODO: Warn if some resources are missing.
        print(f'Resource not found: {filepath}')
        return []

    mdl_parser = import_mdl.MdlParser(self.options, self.mat_manager)
    return mdl_parser.parse_model(filepath)
  
  def parse_textures(self):
    if not self.directory:
      return
    texture_files = self.get_texture_files(self.directory)
    if self.fallback_directory:
      texture_files += self.get_texture_files(self.fallback_directory)
    self.mat_manager.load_textures(texture_files)
  
  def get_texture_files(self, directory):
    texture_files = []
    for filename in os.listdir(directory):
      basename, ext = os.path.splitext(filename)
      if ext.lower() not in ('.rtm', '.vtm'):
        continue
      # TODO: Limit to seen resources only
      if basename.lower()[:2] in ('gm', 'wo'):
        texture_files.append(os.path.join(directory, filename))
    return texture_files

def load(context, filepath,
         *,
         import_shadow_model=False,
         use_vertex_color_materials=False):
  options = import_mdl.Options(import_shadow_model, use_vertex_color_materials)

  # TODO: Wrap with try-except block
  parser = GsdParser(options)
  parser.parse(filepath)
  parser.parse_textures()

  return 'FINISHED', ''