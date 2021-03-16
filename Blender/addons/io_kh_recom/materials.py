# pylint: disable=import-error

if "bpy" in locals():
  # pylint: disable=used-before-assignment
  import importlib
  if "readutil" in locals():
    importlib.reload(readutil)

import bpy

from . import readutil


class ImageImportError(Exception):
  pass


class MaterialManager:
  def __init__(self, options):
    # {texture name -> (material, use_vertex_color)}
    self._material_map = dict()
    # {texture name -> (processed)}
    self._processed_map = dict()
    self._options = options

  def get_material(self, texture_name, use_vertex_color=False):
    if texture_name in self._material_map:
      return self._material_map[texture_name][0]

    material = bpy.data.materials.new(name=texture_name)
    material.use_nodes = True

    bsdf = material.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Specular'].default_value = 0

    self._material_map[texture_name] = material, use_vertex_color
    return material

  def load_textures(self, filepaths):
    for filepath in filepaths:
      self._load_texture_archive(filepath)

  def _load_texture_archive(self, filepath):
    f = readutil.BinaryFileReader(filepath)
    readutil.maybe_skip_ps4_header(f)

    texture_files = readutil.read_rsrc_header(f)
    for texture_name, byte_offs, byte_size in texture_files:
      if texture_name[-4:] == '.tm2':
        texture_name = texture_name[:-4]
      self._load_single_texture(f, texture_name, byte_offs, byte_size)

  def _load_single_texture(self, f, texture_name, offs, size):
    if texture_name not in self._material_map:
      print(f'Texture is unused: {texture_name}')
      return
    if texture_name in self._processed_map:
      return

    f.seek(offs)
    if f.read_uint32() != 0x324D4954:  # "TIM2"
      print(f'Not a TIM2 file: {texture_name}')
      return
    f.skip(2)
    image_count = f.read_uint16()

    # Parse first image header
    f.seek(offs + 0x18)
    image_data_size = f.read_uint32()
    _, color_count = f.read_nuint16(2)
    _, mipmap_count, _, image_format = f.read_nuint8(4)
    width, height = f.read_nuint16(2)

    image_data_offs = offs + 0x10 + image_count * 0x30
    image_data_offs += (mipmap_count - 1) * 0x10
    f.seek(image_data_offs)
    image = f.read_nuint8(image_data_size)
    clut = [[((col >> (i * 8)) & 0xFF) / f
             for i, f in zip(range(4), (0xFF, 0xFF, 0xFF, 0x80))]
            for col in f.read_nuint32(color_count)]

    pixels = [0] * width * height * 4
    if image_format == 0x5:  # 8-bit indexed
      for i in range(width * height):
        p = image[i]
        # Flip bits 4 and 5
        p = ((p >> 1) & 0x8) | ((p << 1) & 0x10) | (p & 0xE7)
        # Pre-flip the image for it to export correctly.
        dstoffs = ((height - (i // width) - 1) * width + (i % width)) * 4
        pixels[dstoffs:dstoffs + 4] = clut[p]
    elif image_format == 0x4:  # 4-bit indexed
      for i in range(width * height):
        p = (image[i // 2] >> (4 if i % 2 == 1 else 0)) & 0xF
        dstoffs = ((height - (i // width) - 1) * width + (i % width)) * 4
        pixels[dstoffs:dstoffs + 4] = clut[p]
    else:
      raise ImageImportError(
          f'Unhandled image pixel format {image_format} for texture {texture_name}'
      )

    image = bpy.data.images.new(f'{texture_name}.png',
                                width=width,
                                height=height)
    image.pixels = pixels
    image.update()

    material, use_vertex_color = self._material_map[texture_name]

    tex_node = material.node_tree.nodes.new('ShaderNodeTexImage')
    tex_node.image = image

    self._processed_map[texture_name] = True

    if use_vertex_color and self._options.USE_VERTEX_COLOR_MATERIALS:
      vcol_node = material.node_tree.nodes.new('ShaderNodeVertexColor')

      # Vertex colors in KH:ReCOM can exceed 1.0. Blender will clamp any vertex
      # color components over 1.0 (stored internally as 8-bit sRGB). To avoid
      # losing color information, the importer halves each vertex color. Here
      # we restore the vertex color back to its original intensity, with the
      # caveat that Blender may not render certain vertex colors as bright as
      # they appear in-game.
      add_node = material.node_tree.nodes.new('ShaderNodeMixRGB')
      add_node.blend_type = 'ADD'
      add_node.inputs['Fac'].default_value = 1.0
      material.node_tree.links.new(add_node.inputs['Color1'],
                                   vcol_node.outputs['Color'])
      material.node_tree.links.new(add_node.inputs['Color2'],
                                   vcol_node.outputs['Color'])

      mult_node = material.node_tree.nodes.new('ShaderNodeMixRGB')
      mult_node.blend_type = 'MULTIPLY'
      mult_node.inputs['Fac'].default_value = 1.0
      material.node_tree.links.new(mult_node.inputs['Color1'],
                                   tex_node.outputs['Color'])
      material.node_tree.links.new(mult_node.inputs['Color2'],
                                   add_node.outputs['Color'])

      alpha_mult_node = material.node_tree.nodes.new('ShaderNodeMath')
      alpha_mult_node.operation = 'MULTIPLY'
      material.node_tree.links.new(alpha_mult_node.inputs[0],
                                   tex_node.outputs['Alpha'])
      material.node_tree.links.new(alpha_mult_node.inputs[1],
                                   vcol_node.outputs['Alpha'])

      bsdf = material.node_tree.nodes['Principled BSDF']
      bsdf.inputs['Specular'].default_value = 0
      material.node_tree.links.new(bsdf.inputs['Base Color'],
                                   mult_node.outputs['Color'])
      material.node_tree.links.new(bsdf.inputs['Alpha'],
                                   alpha_mult_node.outputs['Value'])

    else:
      bsdf = material.node_tree.nodes['Principled BSDF']
      bsdf.inputs['Specular'].default_value = 0
      material.node_tree.links.new(bsdf.inputs['Base Color'],
                                   tex_node.outputs['Color'])
      material.node_tree.links.new(bsdf.inputs['Alpha'],
                                   tex_node.outputs['Alpha'])
