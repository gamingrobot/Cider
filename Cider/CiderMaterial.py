import bpy
from bl_ui.generic_ui_list import draw_ui_list

class CiderLinePreset(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name='Name', default="LinePreset", options={'LIBRARY_EDITABLE'}, override={'LIBRARY_OVERRIDABLE'})
    number: bpy.props.IntProperty(name='Test', default=0, options={'LIBRARY_EDITABLE'}, override={'LIBRARY_OVERRIDABLE'})

    def draw_ui(self, layout):
        row = layout.row(align=True)
        result = row.split()
        result.prop(self, 'number')

class CiderMaterial(bpy.types.PropertyGroup):
    #line_setting: bpy.props.PointerProperty(name="Line Settings", type=CiderLineSettings, options={'LIBRARY_EDITABLE'}, override={'LIBRARY_OVERRIDABLE'})
    #enabled: bpy.props.BoolProperty(name='Enable Cider', default=True)
    line_preset_index: bpy.props.IntProperty(name="Line Preset Index", default=0)

    def draw_ui(self, layout, context):
        pipeline = context.scene.cider
        layout.active = self.id_data.library is None #only local data can be edited
        row = layout.row()
        row.template_list("CIDER_UL_LinePresets", "", pipeline, "line_presets", self, "line_preset_index")
        col = row.column()
        col.operator("wm.cider_add_line_preset", icon='ADD', text='')
        remove_op = col.operator("wm.cider_remove_line_preset", icon='REMOVE', text='')
        remove_op.index = self.line_preset_index
        if self.line_preset_index >= 0 and pipeline.line_presets:
            item = pipeline.line_presets[self.line_preset_index]
            item.draw_ui(layout)

class CIDER_PT_MaterialSettings(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'

    bl_context = "material"
    bl_label = "Cider"

    @classmethod
    def poll(cls, context):
        return context.scene.cider.enabled and context.object is not None

    def draw(self, context):
        layout = self.layout
        if context.material:
            context.material.cider.draw_ui(layout, context)

class CIDER_UL_LinePresets(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        custom_icon = "LINE_DATA"
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.prop(item, "name", text="", emboss=False, icon=custom_icon)
        elif self.layout_type == 'GRID':
            layout.label(text="", icon=custom_icon)

class OT_CiderAddLinePreset(bpy.types.Operator):
    bl_idname = "wm.cider_add_line_preset"
    bl_label = "Add Line Preset"
    
    @classmethod
    def poll(cls, context):
        return context.scene.cider.enabled

    def execute(self, context):
        item = context.scene.cider.line_presets.add()
        item.name = "LinePreset." + f"{len(context.scene.cider.line_presets)}".zfill(3)
        item.number = 12
        return {'FINISHED'}


class OT_CiderRemoveLinePreset(bpy.types.Operator):
    bl_idname = "wm.cider_remove_line_preset"
    bl_label = "Remove Line Preset"
    
    @classmethod
    def poll(cls, context):
        return context.scene.cider.enabled

    index: bpy.props.IntProperty()
    
    def execute(self, context):
        collection = context.scene.cider.line_presets
        if 0 <= self.index < len(collection):
            collection.remove(self.index)
            index = min(max(0, index - 1), len(collection) - 1)
        return {'FINISHED'}


classes = (
    CiderLinePreset,
    CiderMaterial,
    CIDER_PT_MaterialSettings,
    CIDER_UL_LinePresets,
    OT_CiderAddLinePreset,
    OT_CiderRemoveLinePreset
)    

def register():
    for _class in classes: bpy.utils.register_class(_class)
    bpy.types.Material.cider = bpy.props.PointerProperty(type=CiderMaterial)

def unregister():
    for _class in reversed(classes): bpy.utils.unregister_class(_class)
