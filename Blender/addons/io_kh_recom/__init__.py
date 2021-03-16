# pylint: disable=import-error

bl_info = {
    "name":
        "Kingdom Hearts Re:Chain of Memories",
    "author":
        "Murugo",
    "version": (0, 1, 0),
    "blender": (2, 80, 0),
    "location":
        "File -> Import-Export",
    "description":
        "Import-Export Kingdom Hearts Re:Chain of Memories (PS2) models, Import models from KH Re:COM file formats.",
    "category":
        "Import-Export"
}

if "bpy" in locals():
  # pylint: disable=undefined-variable
  import importlib
  if "import_azf" in locals():
    importlib.reload(import_azf)
  if "import_gsd" in locals():
    importlib.reload(import_gsd)
  if "import_mdl" in locals():
    importlib.reload(import_mdl)

import bpy
from bpy.props import (
    BoolProperty,
    StringProperty,
)
from bpy_extras.io_utils import (
    ImportHelper,)


class ImportKhReComAzf(bpy.types.Operator, ImportHelper):
  """Load a Kingdom Hearts Re:Chain of Memories AZF file"""
  bl_idname = "import_khrecom.azf"
  bl_label = "Import Kingdom Hearts Re:COM (PS2) Stage (AZF)"
  bl_options = {'PRESET', 'UNDO'}

  filename_ext = ".azf"
  filter_glob: StringProperty(default="*.azf", options={'HIDDEN'})

  import_skybox: BoolProperty(
      name="Import Skybox",
      description="Import skybox objects and textures.",
      default=True,
  )

  ignore_placeholders: BoolProperty(
      name="Ignore Placeholders",
      description=
      "Skip importing placeholder meshes used to mark particle effects.",
      default=True,
  )

  use_vertex_color_materials: BoolProperty(
      name="Use Vertex Color in Materials",
      description=
      "Automatically connect baked vertex colors in Blender materials if present. If unchecked, vertex color layers will still be imported for objects.",
      default=True,
  )

  def execute(self, context):
    from . import import_azf

    keywords = self.as_keywords(ignore=("filter_glob",))
    status, msg = import_azf.load(context, **keywords)
    if msg:
      self.report({'ERROR'}, msg)
    return {status}

  def draw(self, context):
    pass


class AZF_PT_import_options(bpy.types.Panel):
  bl_space_type = 'FILE_BROWSER'
  bl_region_type = 'TOOL_PROPS'
  bl_label = "Import AZF"
  bl_parent_id = "FILE_PT_operator"

  @classmethod
  def poll(cls, context):
    sfile = context.space_data
    operator = sfile.active_operator

    return operator.bl_idname == "IMPORT_KHRECOM_OT_azf"

  def draw(self, context):
    layout = self.layout
    layout.use_property_split = True
    layout.use_property_decorate = False

    sfile = context.space_data
    operator = sfile.active_operator

    layout.prop(operator, 'import_skybox')
    layout.prop(operator, 'ignore_placeholders')
    layout.prop(operator, 'use_vertex_color_materials')


class ImportKhReComGsd(bpy.types.Operator, ImportHelper):
  """Load a Kingdom Hearts Re:Chain of Memories GSD file"""
  bl_idname = "import_khrecom.gsd"
  bl_label = "Import Kingdom Hearts Re:COM (PS2) Stage Gimmicks (GSD)"
  bl_options = {'PRESET', 'UNDO'}

  filename_ext = ".gsd"
  filter_glob: StringProperty(default="*.gsd", options={'HIDDEN'})

  import_shadow_model: BoolProperty(
      name="Import Shadow Models",
      description="Import models used for shadows.",
      default=False,
  )

  use_vertex_color_materials: BoolProperty(
      name="Use Vertex Color in Materials",
      description=
      "Automatically connect baked vertex colors in Blender materials if present. If unchecked, vertex color layers will still be imported for objects.",
      default=True,
  )

  def execute(self, context):
    from . import import_gsd

    keywords = self.as_keywords(ignore=("filter_glob",))
    status, msg = import_gsd.load(context, **keywords)
    if msg:
      self.report({'ERROR'}, msg)
    return {status}

  def draw(self, context):
    pass


class GSD_PT_import_options(bpy.types.Panel):
  bl_space_type = 'FILE_BROWSER'
  bl_region_type = 'TOOL_PROPS'
  bl_label = "Import GSD"
  bl_parent_id = "FILE_PT_operator"

  @classmethod
  def poll(cls, context):
    sfile = context.space_data
    operator = sfile.active_operator

    return operator.bl_idname == "IMPORT_KHRECOM_OT_gsd"

  def draw(self, context):
    layout = self.layout
    layout.use_property_split = True
    layout.use_property_decorate = False

    sfile = context.space_data
    operator = sfile.active_operator

    layout.prop(operator, 'import_shadow_model')
    layout.prop(operator, 'use_vertex_color_materials')


class ImportKhReComMdl(bpy.types.Operator, ImportHelper):
  """Load a Kingdom Hearts Re:Chain of Memories MDL file"""
  bl_idname = "import_khrecom.mdl"
  bl_label = "Import Kingdom Hearts Re:COM (PS2) Model (MDL)"
  bl_options = {'PRESET', 'UNDO'}

  filename_ext = ".mdl"
  filter_glob: StringProperty(default="*.mdl", options={'HIDDEN'})

  import_shadow_model: BoolProperty(
      name="Import Shadow Models",
      description="Import models used for shadows.",
      default=False,
  )

  use_vertex_color_materials: BoolProperty(
      name="Use Vertex Color in Materials",
      description=
      "Automatically connect baked vertex colors in Blender materials if present. If unchecked, vertex color layers will still be imported for objects.",
      default=True,
  )

  def execute(self, context):
    from . import import_mdl

    keywords = self.as_keywords(ignore=("filter_glob",))
    status, msg = import_mdl.load(context, **keywords)
    if msg:
      self.report({'ERROR'}, msg)
    return {status}

  def draw(self, context):
    pass


class MDL_PT_import_options(bpy.types.Panel):
  bl_space_type = 'FILE_BROWSER'
  bl_region_type = 'TOOL_PROPS'
  bl_label = "Import MDL"
  bl_parent_id = "FILE_PT_operator"

  @classmethod
  def poll(cls, context):
    sfile = context.space_data
    operator = sfile.active_operator

    return operator.bl_idname == "IMPORT_KHRECOM_OT_mdl"

  def draw(self, context):
    layout = self.layout
    layout.use_property_split = True
    layout.use_property_decorate = False

    sfile = context.space_data
    operator = sfile.active_operator

    layout.prop(operator, 'import_shadow_model')
    layout.prop(operator, 'use_vertex_color_materials')


def menu_func_import(self, context):
  self.layout.operator(ImportKhReComAzf.bl_idname,
                       text="Kingdom Hearts Re:COM Stage (.azf)")
  self.layout.operator(ImportKhReComGsd.bl_idname,
                       text="Kingdom Hearts Re:COM Stage Gimmicks (.gsd)")
  self.layout.operator(ImportKhReComMdl.bl_idname,
                       text="Kingdom Hearts Re:COM Model (.mdl)")


classes = (
    ImportKhReComAzf,
    ImportKhReComGsd,
    ImportKhReComMdl,
    AZF_PT_import_options,
    GSD_PT_import_options,
    MDL_PT_import_options,
)


def register():
  for cls in classes:
    bpy.utils.register_class(cls)

  bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
  for cls in classes:
    bpy.utils.unregister_class(cls)

  bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
  register()
