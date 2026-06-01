{
    "name": "POS Promotions by Complete Blocks",
    "summary": "Apply POS discount promotions only on complete quantity blocks like 2x1, 3x2 or 6x5.",
    "version": "19.0.1.0.0",
    "category": "Point of Sale",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": ["pos_loyalty"],
    "data": [
        "views/loyalty_reward_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_promo_by_blocks/static/src/js/pos_promo_by_blocks.js",
        ],
    },
    "installable": True,
    "application": False,
}
