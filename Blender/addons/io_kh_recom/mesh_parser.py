# pylint: disable=import-error

import bpy
import math
import mathutils


class MeshImportError(Exception):
  pass


class Armature:
  def __init__(self, basename, skip_armature_creation=False):
    if not skip_armature_creation:
      self.armature_data = bpy.data.armatures.new('%s_Armature' % basename)
      self.armature_obj = bpy.data.objects.new("%s_Armature" % basename,
                                               self.armature_data)

      bpy.context.scene.collection.objects.link(self.armature_obj)
      bpy.context.view_layer.objects.active = self.armature_obj

    self.bone_matrices = []
    self.bone_names = []


class Submesh:
  def __init__(self, object_name, armature, invert_normals=False):
    self._armature = armature
    self.invert_normals = invert_normals

    self.vtx = []
    self.vn = []
    self.uv = []
    self.vcol = []
    self.tri = []
    self.bone_vertex_list = [[] for _ in range(len(armature.bone_names))]

    self.mesh_data = bpy.data.meshes.new(object_name + '_mesh_data')
    self.mesh_obj = bpy.data.objects.new(object_name, self.mesh_data)

  def update(self, skip_vertex_groups=False):
    self.mesh_data.from_pydata(self.vtx, [], self.tri)
    self.mesh_data.update()

    if self.vcol:
      self.mesh_data.vertex_colors.new()
      self.mesh_data.vertex_colors[-1].data.foreach_set('color', [
          rgba for col in
          [self.vcol[loop.vertex_index] for loop in self.mesh_data.loops]
          for rgba in col
      ])

    if self.uv:
      self.mesh_data.uv_layers.new(do_init=False)
      self.mesh_data.uv_layers[-1].data.foreach_set('uv', [
          vt for pair in
          [self.uv[loop.vertex_index] for loop in self.mesh_data.loops]
          for vt in pair
      ])

    if self.invert_normals:
      self.mesh_data.flip_normals()

    if skip_vertex_groups:
      return
    for i, v_list in enumerate(self.bone_vertex_list):
      if not v_list:
        continue
      group = self.mesh_obj.vertex_groups.new(name=self._armature.bone_names[i])
      for v, weight in v_list:
        group.add([v], weight, 'ADD')

  def update_normals(self):
    if not self.vn:
      return

    vn_loop = []
    for face in self.mesh_data.polygons:
      for vertex_index in face.vertices:
        vn_loop.append(self.vn[vertex_index])
      face.use_smooth = True
    self.mesh_data.use_auto_smooth = True
    self.mesh_data.normals_split_custom_set(vn_loop)


class MeshParser:
  def __init__(self,
               mat_manager,
               armature=None,
               skip_armature_creation=False,
               skip_textureless_meshes=False):
    self._mat_manager = mat_manager
    self._armature = armature
    self._skip_armature_creation = skip_armature_creation
    self._skip_textureless_meshes = skip_textureless_meshes
    self._texture_names = []

  def parse(self, f, model_offs, basename):
    f.seek(model_offs + 0xC)
    texture_table_count = f.read_uint32()
    texture_table_offs = model_offs + f.read_uint32()
    vif_opaque_offs = f.read_uint32()
    vif_translucent_offs = f.read_uint32()

    if texture_table_count == 0 and self._skip_textureless_meshes:
      return [], self._armature

    if not self._armature:
      self._armature = self._parse_armature(f, model_offs, basename)

    self.texture_names = self._parse_texture_table(f, texture_table_offs,
                                                   texture_table_count)

    objects = []
    if vif_opaque_offs:
      objects += self._parse_vif_packets(f, model_offs + vif_opaque_offs,
                                         basename, False)
    if vif_translucent_offs:
      objects += self._parse_vif_packets(f, model_offs + vif_translucent_offs,
                                         basename, True)

    return objects, self._armature

  def _parse_armature(self, f, model_offs, armature_basename):
    armature = Armature(armature_basename, self._skip_armature_creation)

    f.seek(model_offs)
    bone_count = f.read_uint16()
    if bone_count <= 0:
      return
    armature.bone_matrices = [None] * bone_count
    armature.bone_names = [None] * bone_count
    f.skip(2)
    bone_table_offs = model_offs + f.read_uint32()
    transform_table_offs = model_offs + f.read_uint32()

    if not self._skip_armature_creation:
      current_mode = bpy.context.object.mode
      bpy.ops.object.mode_set(mode='EDIT', toggle=False)

    for i in range(bone_count):
      f.seek(bone_table_offs + i * 0x14)
      bone_name = f.read_string(0x10)
      parent_index = f.read_int16()
      bone_index = i

      f.seek(transform_table_offs + i * 0x40)
      local_matrix = mathutils.Matrix([f.read_nfloat32(4) for _ in range(4)])
      local_matrix.transpose()

      if parent_index >= 0:
        global_matrix = armature.armature_data.edit_bones[
            parent_index].matrix @ local_matrix
      else:
        global_matrix = local_matrix

      armature.bone_matrices[bone_index] = global_matrix
      armature.bone_names[bone_index] = bone_name

      if not self._skip_armature_creation:
        bone = armature.armature_data.edit_bones.new(bone_name)
        bone.tail = (0.025, 0, 0)
        bone.use_inherit_rotation = True
        bone.use_local_location = True
        bone.matrix = global_matrix
        if parent_index >= 0:
          bone.parent = armature.armature_data.edit_bones[parent_index]

    if not self._skip_armature_creation:
      armature.armature_obj.rotation_euler = (math.pi / 2, 0, 0)
      bpy.ops.object.mode_set(mode=current_mode, toggle=False)
      armature.armature_obj.select_set(state=True)

    return armature

  def _parse_texture_table(self, f, texture_table_offs, texture_table_count):
    f.seek(texture_table_offs)
    return [f.read_string(0x20) for i in range(texture_table_count)]

  def _parse_vif_packets(self, f, offs, basename, is_translucent):
    # {material index -> Submesh}
    submesh_dict = dict()
    mesh_index = 0
    while offs < f.filesize:
      f.seek(offs)
      dmatag = f.read_uint32()
      if dmatag == 0x60000000:  # ret
        break
      qwc = dmatag & 0xFF

      # Skip STCYCL and UNPACK commands and go straight to compressed vertex
      # data since these are not critical for parsing.
      f.skip(0x10)
      vertex_table_count, _, vertex_count, _, mode = f.read_nuint16(5)

      # TODO: These are known render modes across .AZF and .MDL files, but their
      # exact distinctions are unknown. The render mode specifies which
      # microsubroutine to run in order to process vertex data and send draw
      # instructions to the GIF.
      has_vnormal = has_uv = has_vcol = has_uint_vcol = False
      invert_normals = False
      if mode == 0x10:  # Pos
        vertex_byte_size = 0x20
      elif mode == 0x6:  # Pos, UV
        vertex_byte_size = 0x30
        has_uv = True
      elif mode == 0x4205:  # Pos, UV (Musashi reflective texture?)
        vertex_byte_size = 0x30
        has_uv = True
      elif mode == 0x4009:  # Pos, Color (Musashi inverse hull)
        vertex_byte_size = 0x30
        has_vcol = True
        invert_normals = True
      elif mode in (0x0, 0x5, 0x24, 0x200, 0x406, 0x400B):  # Pos, Color, UV
        vertex_byte_size = 0x40
        has_uv = True
        has_vcol = True
        has_uint_vcol = mode in (0x0, 0x5, 0x24, 0x200)
      elif mode == 0x406E:  # Pos, Normal, Color, UV (Musashi stages)
        vertex_byte_size = 0x50
        has_vnormal = True
        has_uv = True
        has_vcol = True
      else:
        raise MeshImportError('Unrecognized render mode {} at offset {}'.format(
            hex(mode), hex(offs + 0x1C)))

      # Only the first vertex determines the texture to apply.
      if has_uv and mode != 0x4205:
        f.seek(offs + vertex_byte_size + 0x2C)
        texture_index = f.read_uint16()
      else:
        texture_index = 0

      if texture_index in submesh_dict:
        submesh = submesh_dict[texture_index]
      else:
        submesh = submesh_dict[texture_index] = Submesh(
            '{}_mat{}{}'.format(basename, texture_index,
                                '_t' if is_translucent else ''), self._armature,
            invert_normals)

      v_start = len(submesh.vtx)
      v_offs = offs + 0x30
      vertex_table_index = 0
      for v in range(vertex_count):
        # Scan forward for vertices that should be added together due to
        # multiple bone influences.
        f.seek(v_offs + 0x8)
        split_index = f.read_int16()
        split_count = 1
        if split_index > 0:
          # Assume max influence of 8 bones.
          for i in range(min(8, vertex_table_count - vertex_table_index - 1)):
            f.seek(v_offs + (i + 1) * vertex_byte_size + 0x8)
            next_split_index = f.read_int16()
            if next_split_index <= split_index:
              break
            split_index = next_split_index
            split_count += 1

        vtx = []
        for i in range(split_count):
          vertex_table_index += 1
          f.seek(v_offs)
          flag = f.read_int16()
          f.skip(2)
          vtx_weight = f.read_float32()

          f.skip(8)
          vtx_local = f.read_nfloat32(3) + (vtx_weight,)
          f.skip(2)
          bone_index = f.read_int16()
          if bone_index < 0 or bone_index >= len(self._armature.bone_names):
            raise MeshImportError('Bad bone index {} at offset {}'.format(
                bone_index, hex(v_offs)))
          submesh.bone_vertex_list[bone_index].append((v_start + v, vtx_weight))
          vtx.append(self._armature.bone_matrices[bone_index]
                     @ mathutils.Vector(vtx_local))

          if has_vnormal:
            vn = f.read_nfloat32(4)[:3]

          if has_vcol:
            if has_uint_vcol:
              vcol = [
                  c / f for c, f in zip(f.read_nuint32(4), (0x100, 0x100, 0x100,
                                                            0x80))
              ]
            else:
              vcol = [
                  c / f for c, f in zip(f.read_nfloat32(4), (256.0, 256.0,
                                                             256.0, 128.0))
              ]
          if has_uv:
            uv = f.read_nfloat32(2)

          v_offs += vertex_byte_size

        v_mixed = mathutils.Vector((0, 0, 0, 0))
        for v_elem in vtx:
          v_mixed += v_elem
        submesh.vtx.append(v_mixed.to_3d().to_tuple())
        if has_vnormal:
          submesh.vn.append(vn)
        if has_vcol:
          submesh.vcol.append(vcol)
        if has_uv:
          submesh.uv.append((uv[0], 1.0 - uv[1]))
        if v > 1:
          if flag == 0x00:
            submesh.tri.append((v_start + v, v_start + v - 1, v_start + v - 2))
          elif flag == 0x20:
            submesh.tri.append((v_start + v - 2, v_start + v - 1, v_start + v))

      mesh_index += 1
      offs += (qwc + 1) * 0x10

    objects = []
    for texture_index, mesh in submesh_dict.items():
      mesh.update(skip_vertex_groups=self._skip_armature_creation)
      # Objects such as placeholders for particle effects may have UVs, but no
      # textures.
      if has_uv and texture_index < len(self.texture_names):
        material = self._mat_manager.get_material(
            self.texture_names[texture_index], has_vcol)
        mesh.mesh_obj.data.materials.append(material)
      objects.append(mesh.mesh_obj)

      bpy.context.scene.collection.objects.link(mesh.mesh_obj)

      mesh.update_normals()
      mesh.mesh_obj.select_set(state=True)

    return objects
