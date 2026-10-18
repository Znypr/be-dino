"""Start-up script for `python tools/dev_env_check.py --launch blender` (docs/165).

Run INSIDE Blender (`blender --python tools/blender/enable_mcp_addon.py`). It only makes sure the
"MCP for Blender" add-on (module blender_mcp) is switched on for this session. The add-on then
starts its own server on port 9876 by itself (scene option "Auto-Start Server" is on by default).

It never saves preferences, never touches the scene and does nothing if the add-on is already on
(which is the normal case on this PC) or is not installed.
"""
MODULE = "blender_mcp"

try:
    import bpy
    import addon_utils
except ImportError:  # run outside Blender: say so and stop
    print("enable_mcp_addon.py must run inside Blender (blender --python ...)")
    bpy = None


def main():
    if bpy is None:
        return
    installed = any(m.__name__ == MODULE for m in addon_utils.modules())
    if not installed:
        print("enable_mcp_addon: add-on %s is not installed; nothing to do" % MODULE)
        return
    _enabled, loaded = addon_utils.check(MODULE)
    if loaded:
        print("enable_mcp_addon: %s already on" % MODULE)
        return
    try:
        bpy.ops.preferences.addon_enable(module=MODULE)
        print("enable_mcp_addon: switched %s on for this session" % MODULE)
    except Exception as e:  # never stop Blender from starting
        print("enable_mcp_addon: could not enable %s (%s)" % (MODULE, e.__class__.__name__))


main()
