# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8-80 compliant>

bl_info = {
    "name": "Combat Mission MDR format",
    "author": "Stanislav Bobovych",
    "version": (0, 9, 1),
    "blender": (2, 79, 0),
    "location": "File > Import-Export",
    "description": "Import-Export MDR, Import MDR mesh, UV's, materials and textures",
    "warning": "",
    "wiki_url": "https://github.com/sbobovyc/CM2Tools/wiki",
    "support": 'TESTING',
    "category": "Import-Export"}

if "bpy" in locals():
    import importlib
    if "import_mdr" in locals():
        importlib.reload(import_mdr)
    if "export_mdr" in locals():
       importlib.reload(export_mdr)


import bpy
from bpy.props import (
        BoolProperty,
        FloatProperty,
        StringProperty,
        EnumProperty,
        )
from bpy_extras.io_utils import (
        ImportHelper,
        ExportHelper,
        orientation_helper_factory,
        path_reference_mode,
        axis_conversion,
        )


IOOBJOrientationHelper = orientation_helper_factory("IOOBJOrientationHelper", axis_forward='-Z', axis_up='Y')


class ImportMDR(bpy.types.Operator, ImportHelper, IOOBJOrientationHelper):
    """Load a Combat Mission MDR File"""
    bl_idname = "import_scene.mdr"
    bl_label = "Import MDR"
    bl_options = {'PRESET', 'UNDO'}

    filename_ext = ".mdr"
    filter_glob = StringProperty(
            default="*.mdr",
            options={'HIDDEN'},
            )
    use_shadeless = BoolProperty(
        name="Shadeless materials",
        description="Make all materials shadeless",
        default=False,
    )
    use_smooth_shading = BoolProperty(
        name="Use smooth shading",
        description="Make all objects use smooth shading",
        default=True,
    )
    use_transform  = BoolProperty(
        name="Use transform",
        description="Apply transform to object",
        default=False,
    )
    use_recursive_search = BoolProperty(
        name="Recursive image search",
        description="Recursively search for object textures",
        default=True,
    )
    
    def execute(self, context):
        # print("Selected: " + context.active_object.name)
        from . import import_mdr
        """
        if self.split_mode == 'OFF':
            self.use_split_objects = False
            self.use_split_groups = False
        else:
            self.use_groups_as_vgroups = False
        """
        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "filter_glob",
                                            "split_mode",
                                            ))
        """
        global_matrix = axis_conversion(from_forward=self.axis_forward,
                                        from_up=self.axis_up,
                                        ).to_4x4()
        keywords["global_matrix"] = global_matrix
        """

        if bpy.data.is_saved and context.user_preferences.filepaths.use_relative_paths:
            import os
            keywords["relpath"] = os.path.dirname(bpy.data.filepath)
        return import_mdr.load(context, **keywords)
                       
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.prop(self, "use_shadeless")
        layout.prop(self, "use_smooth_shading")
        layout.prop(self, "use_transform")
        layout.prop(self, "use_recursive_search")

class ExportMDR(bpy.types.Operator, ExportHelper, IOOBJOrientationHelper):
    """Save a Combat Mission MDR File"""

    bl_idname = "export_scene.mdr"
    bl_label = 'Export MDR'
    bl_options = {'PRESET'}

    filename_ext = ".mdr"
    filter_glob = StringProperty(
            default="*.mdr",
            options={'HIDDEN'},
            )
    var_float = FloatProperty(
            name="Variable float",
            description="Variable float for testing",
            min=0.0, max=1000.0,
            soft_min=0.0, soft_max=1.0,
            default=1.0,
            )

    path_mode = path_reference_mode

    check_extension = True

    def execute(self, context):
        from . import export_mdr

        from mathutils import Matrix
        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "global_scale",
                                            "check_existing",
                                            "filter_glob",
                                            ))

        # global_matrix = (Matrix.Scale(self.global_scale, 4) *
        #                  axis_conversion(to_forward=self.axis_forward,
        #                                  to_up=self.axis_up,
        #                                  ).to_4x4())
        #
        # keywords["global_matrix"] = global_matrix
        return export_mdr.save(self, context, **keywords)


def menu_func_import(self, context):
    self.layout.operator(ImportMDR.bl_idname, text="CMx2 MDR (.mdr)")


def menu_func_export(self, context):
    self.layout.operator(ExportMDR.bl_idname, text="CMx2 MDR (.mdr)")


def register():
    bpy.utils.register_module(__name__)

    bpy.types.INFO_MT_file_import.append(menu_func_import)
    bpy.types.INFO_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_module(__name__)

    bpy.types.INFO_MT_file_import.remove(menu_func_import)
    bpy.types.INFO_MT_file_export.remove(menu_func_export)

if __name__ == "__main__":
    register()
