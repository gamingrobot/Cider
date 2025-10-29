import os
import bpy
from Malt.PipelineParameters import Type, Parameter
from . import CiderTextures
from . CiderUtils import is_cider_active

class CiderBoolPropertyWrapper(bpy.types.PropertyGroup):
    boolean : bpy.props.BoolProperty(
        options={'LIBRARY_EDITABLE'}, override={'LIBRARY_OVERRIDABLE'})

class CiderEnumPropertyWrapper(bpy.types.PropertyGroup):
    enum_options : bpy.props.StringProperty(
        options={'LIBRARY_EDITABLE'}, override={'LIBRARY_OVERRIDABLE'})
    
    def get_items(self, context=None):
        for option in self.enum_options.split(','):
            yield (option, option, option)
    
    enum : bpy.props.EnumProperty(items=get_items, name='',
        options={'LIBRARY_EDITABLE'}, override={'LIBRARY_OVERRIDABLE'})

class CiderTexturePropertyWrapper(bpy.types.PropertyGroup):
    texture : bpy.props.PointerProperty(type=bpy.types.Image,
        options={'LIBRARY_EDITABLE'}, override={'LIBRARY_OVERRIDABLE'})

class CiderPropertyGroup(bpy.types.PropertyGroup):

    bools : bpy.props.CollectionProperty(type=CiderBoolPropertyWrapper,
        options={'LIBRARY_EDITABLE'},
        override={'LIBRARY_OVERRIDABLE', 'USE_INSERTION'})
    enums : bpy.props.CollectionProperty(type=CiderEnumPropertyWrapper,
        options={'LIBRARY_EDITABLE'},
        override={'LIBRARY_OVERRIDABLE', 'USE_INSERTION'})
    textures : bpy.props.CollectionProperty(type=CiderTexturePropertyWrapper,
        options={'LIBRARY_EDITABLE'},
        override={'LIBRARY_OVERRIDABLE', 'USE_INSERTION'})    

    parent : bpy.props.PointerProperty(type=bpy.types.ID, name="Override From",
        options={'LIBRARY_EDITABLE'}, override={'LIBRARY_OVERRIDABLE'})
    override_from_parents : bpy.props.CollectionProperty(type=CiderBoolPropertyWrapper,
        options={'LIBRARY_EDITABLE'},
        override={'LIBRARY_OVERRIDABLE', 'USE_INSERTION'})
    show_in_children : bpy.props.CollectionProperty(type=CiderBoolPropertyWrapper,
        options={'LIBRARY_EDITABLE'},
        override={'LIBRARY_OVERRIDABLE', 'USE_INSERTION'})

    def get_rna(self):
        try:
            if '_CIDER_' not in self.keys():
                if '_RNA_UI' in self.keys():
                    old_rna = self['_RNA_UI']
                    self['_CIDER_'] = {k : old_rna[k] for k in old_rna.keys()}
                    self.pop('_RNA_UI')
                else:
                    self['_CIDER_'] = {}
            return self['_CIDER_']
        except:
            return {}

    def setup(self, parameters, replace_parameters=True, reset_to_defaults=False, skip_private=True,
        copy_from=None, copy_map=None):
        rna = self.get_rna()

        copy_values = copy_from is not None
        if copy_from is None and self.parent:
            copy_from = self.parent.cider_parameters
        
        def setup_parameter(name, parameter):
            if name not in rna.keys():
                rna[name] = {}

            type_changed = 'type' not in rna[name].keys() or rna[name]['type'] != parameter.type
            size_changed = 'size' in rna[name].keys() and rna[name]['size'] != parameter.size

            copy_name = name
            if copy_map and name in copy_map:
                copy_name = copy_map[name]

            if copy_from and copy_name in copy_from.get_rna():
                rna_prop = copy_from.get_rna()[copy_name]
                parameter.default_value = rna_prop.get("default")
                parameter.type = rna_prop.get('type')
                parameter.subtype = rna_prop.get('cider_subtype')
                parameter.size = rna_prop.get('size')
                parameter.filter = rna_prop.get('filter')
                if self.parent:
                    parameter.label = rna_prop.get('label')
                parameter.enum_options = rna_prop.get('enum_options')
                parameter.min = rna_prop.get('min')
                parameter.max = rna_prop.get('max')
            
            if hasattr(parameter, 'label') and parameter.label:
                rna[name]['label'] = parameter.label
            else:
                rna[name]['label'] = name.removeprefix('U_0_').replace('_0_','.').replace('_',' ').title()

            if reset_to_defaults:
                #TODO: Rename
                type_changed = True

            def to_basic_type(value):
                try: return tuple(value)
                except: return value
            def equals(a, b):
                return to_basic_type(a) == to_basic_type(b)

            def resize():
                if parameter.size == 1:
                       self[name] = self[name][0]
                else:
                    if rna[name]['size'] > parameter.size:
                        self[name] = self[name][:parameter.size]
                    else:
                        first = self[name]
                        try: first = list(first)
                        except: first = [first]
                        second = list(parameter.default_value)
                        self[name] = first + second[rna[name]['size']:]

            if parameter.type in (Type.INT, Type.FLOAT):
                if type_changed or equals(rna[name]['default'], self[name]):
                    if copy_values and copy_name in copy_from.keys():
                        self[name] = copy_from[copy_name]
                    else:
                        self[name] = parameter.default_value   
                elif size_changed:
                    resize()
            
            if parameter.type == Type.STRING:
                if type_changed or equals(rna[name]['default'], self[name]):
                    if copy_values and copy_name in copy_from.keys():
                        self[name] = copy_from[copy_name]
                    else:
                        self[name] = parameter.default_value  

            if parameter.type == Type.BOOL:
                if name not in self.bools:
                    self.bools.add().name = name
                if type_changed or equals(rna[name]['default'], self.bools[name].boolean):
                    if copy_values and copy_name in copy_from.bools.keys():
                        self.bools[name].boolean = copy_from.bools[copy_name].boolean
                    else:
                        self.bools[name].boolean = parameter.default_value
                elif size_changed:
                    resize()
            
            if parameter.type == Type.ENUM:
                if name not in self.enums:
                    self.enums.add().name = name
                rna[name]['enum_options'] = parameter.enum_options
                self.enums[name].enum_options = ','.join(parameter.enum_options)
                if type_changed or equals(rna[name]['default'], self.enums[name].enum):
                    if copy_values and copy_name in copy_from.enums.keys():
                        self.enums[name].enum = copy_from.enums[copy_name].enum
                    else:
                        self.enums[name].enum = parameter.default_value
            
            if parameter.type == Type.TEXTURE:
                if name not in self.textures:
                    self.textures.add().name = name
                if type_changed or self.textures[name] == rna[name]['default']:
                    if copy_values and copy_name in copy_from.textures.keys():
                        self.textures[name].texture = copy_from.textures[copy_name].texture
                    elif isinstance(parameter.default_value, bpy.types.Image):
                        self.textures.texture = parameter.default_value
                    
            if name not in self.override_from_parents:
                self.override_from_parents.add().name = name
            if name not in self.show_in_children:
                prop = self.show_in_children.add()
                prop.name = name
                prop.boolean = True

            rna[name]['active'] = True
            rna[name]["default"] = parameter.default_value
            rna[name]['type'] = parameter.type
            rna[name]['cider_subtype'] = parameter.subtype
            rna[name]['size'] = parameter.size
            rna[name]['filter'] = parameter.filter

            rna[name]['min'] = getattr(parameter, 'min', None)
            rna[name]['max'] = getattr(parameter, 'max', None)
            

        #TODO: We should purge non active properties (specially textures)
        # at some point, likely on file save or load 
        # so we don't lose them immediately when changing shaders/pipelines
        if replace_parameters:
            for key, value in rna.items():
                if '@' not in key:
                    rna[key]['active'] = False
        
        for name, parameter in parameters.items():
            if skip_private and (name.isupper() or name.startswith('_')):
                # We treat underscored and all caps uniforms as "private"
                continue
            setup_parameter(name, parameter)

        for key, value in rna.items():
            if '@' in key and key not in parameters.keys():
                main_name = key.split(' @ ')[0]
                rna[key]['active'] = main_name in rna.keys() and rna[main_name]['active'] and rna[key]['active']
                if rna[key]['active']:
                    if rna[key]['type'] != rna[main_name]['type'] or rna[key]['size'] != rna[main_name]['size']:
                        parameter = Parameter(rna[main_name]['default'], rna[main_name]['type'],
                            rna[main_name]['size'], rna[main_name]['filter'], rna[main_name]['cider_subtype'])
                        setup_parameter(key, parameter)
        
        for key, value in rna.items():
            rna_prop = rna[key]
            if rna_prop['active'] == False:
                continue
            if rna_prop['type'] not in (Type.FLOAT, Type.INT) or isinstance(rna_prop['default'], str):
                continue
            #Default to color since it's the most common use case
            cider_subtype = rna_prop.get('cider_subtype')
            if rna_prop['type'] == Type.FLOAT and rna_prop['size'] >= 3 and (cider_subtype is None or cider_subtype == 'Color'):
                rna_prop['subtype'] = 'COLOR'
                rna_prop['soft_min'] = 0.0
                rna_prop['soft_max'] = 1.0
            else:
                rna_prop['subtype'] = 'NONE'

            ui_properties = {}
            for ui_key in ('default', 'subtype', 'min', 'max', 'soft_min', 'soft_max'):
                if ui_key in rna_prop and rna_prop[ui_key] is not None:
                    ui_properties[ui_key] = rna_prop[ui_key]
            
            ui = self.id_properties_ui(key)
            ui.clear()
            ui.update(**ui_properties)

        # Force a depsgraph update. 
        # Otherwise these won't be available inside scene_eval
        self.id_data.update_tag()
        for screen in bpy.data.screens:
            for area in screen.areas:
                area.tag_redraw()
    
    def rename_property(self, old_name, new_name):
        rna = self.get_rna()
        rna[new_name] = rna.pop(old_name)
        type = rna[new_name]['type']
        self.override_from_parents[old_name].name = new_name
        if old_name in self.show_in_children.keys():
            self.show_in_children[old_name].name = new_name
        if type in (Type.FLOAT, Type.INT, Type.STRING):
            self[new_name] = self.pop(old_name)
        elif type == Type.BOOL:
            self.bools[old_name].name = new_name
        elif type == Type.ENUM:
            self.enums[old_name].name = new_name
        elif type == Type.TEXTURE:
            self.textures[old_name].name = new_name
    
    def remove_property(self, name):
        rna = self.get_rna()
        rna_prop = rna[name]
        type = rna_prop['type']
        rna.pop(name)
        def remove(collection, key):
            collection.remove(collection.find(key))
        remove(self.override_from_parents, name)
        remove(self.show_in_children, name)
        if type in (Type.FLOAT, Type.INT, Type.STRING):
            self.pop(name)
        elif type == Type.BOOL:
            remove(self.bools, name)
        elif type == Type.ENUM:
            remove(self.enums, name)
        elif type == Type.TEXTURE:
            remove(self.textures, name)

    def add_override(self, property_name, override_name):
        main_prop = self.get_rna()[property_name]
        new_name = property_name + ' @ ' + override_name
        property = {}
        parameter = Parameter(main_prop['default'], main_prop['type'], main_prop['size'],
            main_prop['filter'], main_prop['cider_subtype'])
        parameter.default_value = main_prop.get("default")
        parameter.type = main_prop.get('type')
        parameter.subtype = main_prop.get('cider_subtype')
        parameter.size = main_prop.get('size')
        parameter.filter = main_prop.get('filter')
        parameter.label = main_prop.get('label') + ' @ ' + override_name
        parameter.enum_options = main_prop.get('enum_options')
        parameter.min = main_prop.get('min')
        parameter.max = main_prop.get('max')
        property[new_name] = parameter
        self.setup(property, replace_parameters= False)
    
    def remove_override(self, property):
        rna = self.get_rna()
        if property in rna:
            rna[property]['active'] = False
            self.id_data.update_tag()
    
    def handle_duplication(self):
        for gradient in self.gradients.values():
            gradient.texture = gradient.texture.copy()

    def get_parameters(self, overrides, proxys):
        if '_CIDER_' not in self.keys():
            return {}
        rna = self.get_rna()
        parameters = {}
        for key in rna.keys():
            if '@' in key:
                continue
            if rna[key]['active'] == False:
                continue
            parameters[key] = self.get_parameter(key, overrides, proxys)
        return parameters
    
    def get_parameter(self, key, overrides, proxys, retrieve_blender_type=False, rna_copy={}):
        if self.parent and self.override_from_parents[key].boolean == False:
            try:
                return self.parent.cider_parameters.get_parameter(key, overrides, proxys, retrieve_blender_type, rna_copy)
            except:
                pass

        rna = self.get_rna()
        rna_copy.update(rna[key])
        for override in reversed(overrides):
            override_key = key + ' @ ' +  override
            if override_key in rna.keys():
                if rna[override_key]['active']:
                    key = override_key
        if rna[key]['active'] == False:
            raise Exception()

        if rna[key]['type'] in (Type.INT, Type.FLOAT):
            try:
                return tuple(self[key])
            except:
                return self[key]
        elif rna[key]['type'] == Type.STRING:
            return self[key]
        elif rna[key]['type'] == Type.BOOL:
            return bool(self.bools[key].boolean)
        elif rna[key]['type'] == Type.ENUM:
            return self.enums[key].enum_options.split(',').index(self.enums[key].enum)
        elif rna[key]['type'] == Type.TEXTURE:
            texture = self.textures[key].texture
            if retrieve_blender_type:
                return texture
            if texture:
                texture_key = ('texture', texture.name_full)
                if texture_key not in proxys.keys():
                    if proxy := CiderTextures.get_texture(texture):
                        proxys[texture_key] = proxy
                    else:
                        return None
                return proxys[texture_key]
            else:
                return None
    
    def draw_ui(self, layout, filter=None):
        layout.use_property_decorate = False
        #layout.prop(self, "parent")

        if '_CIDER_' not in self.keys():
            return #Can't modify ID classes from here
        rna = self.get_rna()

        namespace_stack = [(None, layout)]

        def get_label(key):
            label = rna[key].get('label')
            if self.parent:
                parent_prop = self.parent.cider_parameters.get_rna().get(key)
                if parent_prop:
                    label = parent_prop.get('label', label)
            if label is None:
                label = key.replace('_0_','.').replace('_',' ')
            return label
        
        # Most drivers sort the uniforms in alphabetical order anyway, 
        # so there's no point in tracking the actual index since it doesn't follow
        # the declaration order
        import re
        def natural_sort_labels(k):
            label = get_label(k)
            n_split = re.split('([0-9]+)', label)
            ns_split = []
            for n in n_split:
                ns_split.extend(n.split('.'))
            result = []
            for e in ns_split:
                if e.isdigit():
                    result.append('z')
                    result.append(int(e))
                else:
                    result.append(e)
                    result.append(0)
            return result
        keys = sorted(rna.keys(), key=natural_sort_labels)
        # Put Settings first. Kind of hacky, but ¯\_(ツ)_/¯
        def settings_first(k):
            return not rna[k].get('label', k).startswith('Settings.')
        keys.sort(key=settings_first)
        
        for key in keys:
            if rna[key]['active'] == False:
                continue

            if filter and rna[key]['filter'] and rna[key]['filter'] != filter:
                continue

            labels = get_label(key).split('.')
            label = labels[-1]
            
            #defer layout (box) creation until a property is actually drawn
            def get_layout():
                nonlocal namespace_stack
                layout = None
                if len(labels) == 1:
                    namespace_stack = namespace_stack[:1]
                    layout = namespace_stack[0][1]
                else:
                    for i in range(0, len(labels) - 1):
                        label = labels[i]
                        stack_i = i+1
                        if len(namespace_stack) > stack_i and namespace_stack[stack_i][0] != label:
                            namespace_stack = namespace_stack[:stack_i]
                        if len(namespace_stack) < stack_i+1:
                            box = namespace_stack[stack_i - 1][1].box()
                            box.label(text=label + " :")
                            namespace_stack.append((label, box))
                        layout = namespace_stack[stack_i][1]
                return layout.column()

            def draw_callback(layout, property_group):
                is_self = self.as_pointer() == property_group.as_pointer()
                if self.parent and (is_self == False or self.override_from_parents[key].boolean == True):
                    layout.prop(self.override_from_parents[key], 'boolean', text='')
                if is_self == False:
                    layout.active = False
            
            self.draw_parameter(get_layout, key, label, draw_callback=draw_callback)


    def draw_parameter(self, layout, key, label, draw_callback=None, is_node_socket=False, drawn_from_child=False):
        if self.parent and self.override_from_parents[key].boolean == False:
            if self.parent.cider_parameters.draw_parameter(layout, key, label, draw_callback, is_node_socket, True):
                return True

        rna = self.get_rna()
        
        if key not in rna.keys():
            return False
        
        if drawn_from_child and key in self.show_in_children.keys() and self.show_in_children[key].boolean == False:
            return True

        if callable(layout):
            layout = layout()

        def make_row(label_only = False):
            result = layout
            nonlocal label
            row = layout.row(align=True)
            result = row.split()
            is_override = '@' in key
            
            if is_override:
                if label is None:
                    label = key
                label = '⇲ '+label.split(' @ ')[-1]
            
            if label is not None:
                if label_only == False and is_node_socket == False:          
                    result = result.split(factor=0.66)
                    result.alignment = 'RIGHT'
                result.label(text=label)
            
            if is_override:
                row.operator('wm.cider_callback', text='', icon='X').callback.set(
                    lambda : self.remove_override(key), 'Remove Override')
            else:
                row.operator('wm.cider_new_override', text='', icon='DECORATE_OVERRIDE').callback.set(
                    lambda override_name: self.add_override(key, override_name))
            
            if draw_callback:
                draw_callback(row, self)
            
            return result

        if rna[key]['type'] in (Type.INT, Type.FLOAT, Type.STRING):
            #TODO: add subtype toggle
            slider = rna[key]['cider_subtype'] == 'Slider'
            make_row().prop(self, '["{}"]'.format(key), text='', slider=slider)
        elif rna[key]['type'] == Type.BOOL:
            make_row().prop(self.bools[key], 'boolean', text='')
        elif rna[key]['type'] == Type.ENUM:
            make_row().prop(self.enums[key], 'enum', text='')
        elif rna[key]['type'] == Type.TEXTURE:
            make_row(True)
            row = layout.row(align=True)
            if self.textures[key].texture:
                row = row.split(factor=0.8, align=True)
            row.template_ID(self.textures[key], "texture", new="image.new", open="image.open")
            if self.textures[key].texture:
                row.prop(self.textures[key].texture.colorspace_settings, 'name', text='')
        else:
            make_row(True)
            
        return True


from . import CiderUtils

class OT_CiderNewOverride(bpy.types.Operator):
    bl_idname = "wm.cider_new_override"
    bl_label = "Cider Add A Property Override"
    bl_options = {'INTERNAL'}

    def get_override_enums(self, context):
        overrides = context.scene.cider.overrides.split(',')
        result = []
        for i, override in enumerate(overrides):
            result.append((override, override, '', i))
        return result
    override : bpy.props.EnumProperty(items=get_override_enums,
        options={'LIBRARY_EDITABLE'}, override={'LIBRARY_OVERRIDABLE'})
    
    callback : bpy.props.PointerProperty(type=CiderUtils.CiderCallback,
        options={'LIBRARY_EDITABLE'}, override={'LIBRARY_OVERRIDABLE'})
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "override")
    
    def execute(self, context):
        self.callback.call(self.override)
        return {'FINISHED'}


class CIDER_PT_Base(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "disabled"

    bl_label = "Cider Settings"

    @classmethod
    def get_cider_property_owner(cls, context):
        return None
    
    @classmethod
    def get_parameter_type(cls):
        return None

    @classmethod
    def poll(cls, context):
        if is_cider_active() and cls.get_cider_property_owner(context):
            from Cider.CiderPipeline import get_bridge
            bridge = get_bridge()
            parameter_type = cls.get_parameter_type()
            if bridge is None or parameter_type is None or len(getattr(bridge.parameters, parameter_type)) > 0:
                return True
        return False
    
    def draw(self, context):
        owner = self.__class__.get_cider_property_owner(context)
        if owner:
            self.layout.active = owner.library is None #Only local data can be edited
            owner.cider_parameters.draw_ui(self.layout)

class CIDER_PT_Scene(CIDER_PT_Base):
    bl_context = "scene"
    @classmethod
    def get_parameter_type(cls):
        return 'scene'
    @classmethod
    def get_cider_property_owner(cls, context):
        return context.scene

class CIDER_PT_World(CIDER_PT_Base):
    bl_context = "world"
    @classmethod
    def get_parameter_type(cls):
        return 'world'
    @classmethod
    def get_cider_property_owner(cls, context):
        return context.world

class CIDER_PT_Camera(CIDER_PT_Base):
    bl_context = "data"
    @classmethod
    def get_parameter_type(cls):
        return 'camera'
    @classmethod
    def get_cider_property_owner(cls, context):
        return context.camera

class CIDER_PT_Object(CIDER_PT_Base):
    bl_context = "object"
    @classmethod
    def get_parameter_type(cls):
        return 'object'
    @classmethod
    def get_cider_property_owner(cls, context):
        return context.object

# In CiderMaterial
# class CIDER_PT_Material(CIDER_PT_Base):
#     bl_context = "material"
#     @classmethod
#     def get_cider_property_owner(cls, context):
#         if context.material:
#             return context.material

class CIDER_PT_Mesh(CIDER_PT_Base):
    bl_context = "data"
    @classmethod
    def get_parameter_type(cls):
        return 'mesh'
    @classmethod
    def get_cider_property_owner(cls, context):
        if context.mesh:
            return context.mesh
        if context.curve:
            return context.curve
        if context.meta_ball:
            return context.meta_ball
        if context.object and context.object.type in ('SURFACE', 'FONT'):
            return context.object.data

# class CIDER_PT_Light(CIDER_PT_Base):
#     bl_context = "data"
#     @classmethod
#     def get_parameter_type(cls):
#         return 'light'

#     @classmethod
#     def get_cider_property_owner(cls, context):
#         return context.light

classes = (
    CiderBoolPropertyWrapper,
    CiderEnumPropertyWrapper,
    CiderTexturePropertyWrapper,
    CiderPropertyGroup,
    OT_CiderNewOverride,
    CIDER_PT_Base,
    CIDER_PT_Scene,
    CIDER_PT_World,
    CIDER_PT_Camera,
    CIDER_PT_Object,
    CIDER_PT_Mesh,
    # CIDER_PT_Light,
)

def register():
    for _class in classes: bpy.utils.register_class(_class)

    bpy.types.Scene.cider_parameters = bpy.props.PointerProperty(type=CiderPropertyGroup,
        options={'LIBRARY_EDITABLE'}, override={'LIBRARY_OVERRIDABLE'})
    bpy.types.World.cider_parameters = bpy.props.PointerProperty(type=CiderPropertyGroup,
        options={'LIBRARY_EDITABLE'}, override={'LIBRARY_OVERRIDABLE'})
    bpy.types.Camera.cider_parameters = bpy.props.PointerProperty(type=CiderPropertyGroup,
        options={'LIBRARY_EDITABLE'}, override={'LIBRARY_OVERRIDABLE'})
    bpy.types.Object.cider_parameters = bpy.props.PointerProperty(type=CiderPropertyGroup,
        options={'LIBRARY_EDITABLE'}, override={'LIBRARY_OVERRIDABLE'})
    # bpy.types.Material.cider_parameters = bpy.props.PointerProperty(type=CiderPropertyGroup,
    #     options={'LIBRARY_EDITABLE'}, override={'LIBRARY_OVERRIDABLE'})
    bpy.types.Mesh.cider_parameters = bpy.props.PointerProperty(type=CiderPropertyGroup,
        options={'LIBRARY_EDITABLE'}, override={'LIBRARY_OVERRIDABLE'})
    bpy.types.Curve.cider_parameters = bpy.props.PointerProperty(type=CiderPropertyGroup,
        options={'LIBRARY_EDITABLE'}, override={'LIBRARY_OVERRIDABLE'})
    bpy.types.MetaBall.cider_parameters = bpy.props.PointerProperty(type=CiderPropertyGroup,
        options={'LIBRARY_EDITABLE'}, override={'LIBRARY_OVERRIDABLE'})
    # bpy.types.Light.cider_parameters = bpy.props.PointerProperty(type=CiderPropertyGroup,
    #     options={'LIBRARY_EDITABLE'}, override={'LIBRARY_OVERRIDABLE'})
    bpy.types.FreestyleLineStyle.cider_parameters = bpy.props.PointerProperty(type=CiderPropertyGroup,
        options={'LIBRARY_EDITABLE'}, override={'LIBRARY_OVERRIDABLE'})


def unregister():
    for _class in reversed(classes): bpy.utils.unregister_class(_class)

    del bpy.types.Scene.cider_parameters
    del bpy.types.World.cider_parameters
    del bpy.types.Camera.cider_parameters
    del bpy.types.Object.cider_parameters
    # del bpy.types.Material.cider_parameters
    del bpy.types.Mesh.cider_parameters
    del bpy.types.Curve.cider_parameters
    # del bpy.types.Light.cider_parameters
    del bpy.types.FreestyleLineStyle.cider_parameters

