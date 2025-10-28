bl_info = {
    "name": "Cider",
    "description" : "Line render based on Malt",
    "author" : "gamingrobot, Miguel Pozo",
    "version": (1,0,0,'Release'),
    "blender" : (4, 1, 0),
    "doc_url": "",
    "tracker_url": "",
    "category": "Render"
}

import sys, os
from os import path
import bpy

#Add Malt and dependencies to the import path
__CURRENT_DIR = path.dirname(path.realpath(__file__))
__CIDER_PATH = path.join(__CURRENT_DIR, '.MaltPath')
if __CIDER_PATH not in sys.path: sys.path.append(__CIDER_PATH)
_PY_VERSION = str(sys.version_info[0])+str(sys.version_info[1])
__CIDER_DEPENDENCIES_PATH = path.join(__CIDER_PATH,'Malt','.Dependencies-{}'.format(_PY_VERSION))
if __CIDER_DEPENDENCIES_PATH not in sys.path: sys.path.append(__CIDER_DEPENDENCIES_PATH)

class Preferences(bpy.types.AddonPreferences):
    # this must match the addon name
    bl_idname = __package__
    
    render_fps_cap : bpy.props.IntProperty(name="Max Viewport Render Framerate", default=30)

    def draw(self, context):
        layout = self.layout
        layout.operator('wm.path_open', text="Open Session Log").filepath=sys.stdout.log_path
        layout.prop(self, "render_fps_cap")

class CiderDebugOperator(bpy.types.Operator):
    bl_idname = "wm.cider_debug"
    bl_label = "Cider Debug"

    def execute(self, context):
        import pprint
        #pprint.pprint(context.scene.cider.enabled)
        return{"FINISHED"}

def do_windows_fixes():
    import platform, multiprocessing as mp, ctypes
    from shutil import copy
    # Workaround https://developer.blender.org/rB04c5471ceefb41c9e49bf7c86f07e9e7b8426bb3
    if platform.system() == 'Windows':
        sys.executable = sys._base_executable
        # Use python-gpu on windows (patched python with NvOptimusEnablement and AmdPowerXpressRequestHighPerformance)
        python_gpu_path = path.join(__CIDER_DEPENDENCIES_PATH, 'python-gpu-{}.exe'.format(_PY_VERSION))
        if os.path.exists(python_gpu_path) == False:
            print(f"CIDER WARNING: python-gpu-{_PY_VERSION}.exe not found. Performance might be affected.")
            return
        python_executable = path.join(sys.exec_prefix, 'bin', 'python-gpu-{}.exe'.format(_PY_VERSION))
        if os.path.exists(python_executable) == False:
            try:
                copy(python_gpu_path, python_executable)
            except PermissionError as e:
                command = '/c copy "{}" "{}"'.format(python_gpu_path, python_executable)
                result = ctypes.windll.shell32.ShellExecuteW(None, 'runas', 'cmd.exe', command, None, 0)
        mp.set_executable(python_executable)

def get_modules():
    from . import CiderUtils, CiderMeshes, CiderProperties, CiderLineStyle, CiderMaterial, CiderPipeline, CiderRenderer
    return [ CiderUtils, CiderMeshes, CiderProperties, CiderLineStyle, CiderMaterial, CiderPipeline, CiderRenderer ]


classes=[
    Preferences,
    CiderDebugOperator
]

def register():
    for _class in classes: bpy.utils.register_class(_class)

    import importlib
    for module in get_modules():
        importlib.reload(module)
    
    import Bridge
    Bridge.reload()

    do_windows_fixes()

    for module in get_modules():
        module.register()

def unregister():
    for _class in reversed(classes): bpy.utils.unregister_class(_class)

    for module in reversed(get_modules()):
        module.unregister()
    