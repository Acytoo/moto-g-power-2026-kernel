// SPDX-License-Identifier: GPL-2.0
/* One-shot shutdown of this phone's bound panel through its existing driver.
 * No register writes, GPIO overrides, partition changes or driver unbinding.
 * Default is inspection only; poweroff=1 must be explicitly requested.
 * Unloading does not turn the panel back on. Reboot restores normal startup.
 */
#include <linux/module.h>
#include <linux/of.h>
#include <linux/err.h>
#include <drm/drm_panel.h>

static bool poweroff;
module_param(poweroff, bool, 0400);
MODULE_PARM_DESC(poweroff, "Call the bound panel's disable/unprepare callbacks");

static int __init moto_panel_off_init(void)
{
    struct device_node *node;
    struct drm_panel *panel;
    int ret;

    node = of_find_compatible_node(NULL, NULL,
                                  "tm_ili77600a_vid_1080_2388_fhd_120hz");
    if (!node)
        return -ENODEV;
    panel = of_drm_find_panel(node);
    of_node_put(node);
    if (IS_ERR(panel))
        return PTR_ERR(panel);
    if (!panel->funcs || !panel->funcs->disable || !panel->funcs->unprepare)
        return -EOPNOTSUPP;

    pr_info("moto_panel_off: found bound Tianma ILI77600A panel; poweroff=%d\n",
            poweroff);
    if (!poweroff)
        return 0;

    ret = drm_panel_disable(panel);
    if (ret) {
        pr_err("moto_panel_off: disable failed: %d\n", ret);
        return ret;
    }
    ret = drm_panel_unprepare(panel);
    if (ret) {
        pr_err("moto_panel_off: unprepare failed: %d\n", ret);
        return ret;
    }
    pr_info("moto_panel_off: panel disable and unprepare completed\n");
    return 0;
}

static void __exit moto_panel_off_exit(void)
{
    pr_info("moto_panel_off: helper unloaded; panel state unchanged\n");
}

module_init(moto_panel_off_init);
module_exit(moto_panel_off_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("One-shot headless panel shutdown using the bound vendor driver");
