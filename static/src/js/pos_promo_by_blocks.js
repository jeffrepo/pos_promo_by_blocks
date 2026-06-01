/** @odoo-module **/

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

/**
 * POS block promotions for discount rewards.
 *
 * Standard Odoo specific discounts discount every matching line once the minimum
 * quantity rule is reached. This patch limits the discount base to complete
 * blocks only.
 *
 * Examples:
 *   2x1 => pos_block_qty = 2, pos_block_pay_qty = 1, discount = 50%
 *   3x2 => pos_block_qty = 3, pos_block_pay_qty = 2, discount = 33.333333%
 *   6x5 => pos_block_qty = 6, pos_block_pay_qty = 5, discount = 16.666667%
 */
patch(PosOrder.prototype, {
    _getDiscountableOnSpecific(reward) {
        if (!reward.pos_block_promo) {
            return super._getDiscountableOnSpecific(...arguments);
        }
        return this._getDiscountableOnSpecificByCompleteBlocks(reward);
    },

    _getDiscountableOnSpecificByCompleteBlocks(reward) {
        const blockQty = Number(reward.pos_block_qty || 0);
        const payQty = Number(reward.pos_block_pay_qty || 0);
        if (
            reward.reward_type !== "discount" ||
            reward.discount_mode !== "percent" ||
            reward.discount_applicability !== "specific" ||
            !blockQty ||
            !payQty ||
            payQty >= blockQty
        ) {
            return super._getDiscountableOnSpecific(reward);
        }

        const applicableProductIds = new Set(reward.all_discount_product_ids.map((p) => p.id));
        const orderLines = this.getOrderlines();
        const candidateLines = [];

        // Reproduce the important part of the standard specific-discount base:
        // use the amount still available on each real product line, and never
        // include reward lines as candidate units.
        const remainingAmountPerLine = {};
        for (const line of orderLines) {
            if (!line.getQuantity() || !line.price_unit || line.reward_id) {
                continue;
            }
            remainingAmountPerLine[line.uuid] = line.prices.total_included;
            const productId = line.combo_parent_id?.product_id.id || line.getProduct().id;
            if (applicableProductIds.has(productId)) {
                candidateLines.push(line);
            }
        }

        const totalQty = candidateLines.reduce((total, line) => total + line.getQuantity(), 0);
        const discountableQty = Math.floor(totalQty / blockQty) * blockQty;
        if (discountableQty <= 0) {
            return { discountable: 0, discountablePerTax: {} };
        }

        // When there are mixed products/prices in the same promotion, discount
        // the cheapest units first. This is the safest behavior for the merchant
        // and matches the usual expectation of 2x1/3x2 promotions.
        const sortedLines = candidateLines.toSorted((lineA, lineB) => {
            const unitA = (remainingAmountPerLine[lineA.uuid] || 0) / Math.abs(lineA.getQuantity());
            const unitB = (remainingAmountPerLine[lineB.uuid] || 0) / Math.abs(lineB.getQuantity());
            return unitA - unitB;
        });

        let qtyLeft = discountableQty;
        let discountable = 0;
        const discountablePerTax = {};

        for (const line of sortedLines) {
            if (qtyLeft <= 0) {
                break;
            }
            const lineQty = Math.abs(line.getQuantity());
            const qtyFromLine = Math.min(qtyLeft, lineQty);
            if (qtyFromLine <= 0) {
                continue;
            }

            const ratio = qtyFromLine / lineQty;
            const lineRemaining = remainingAmountPerLine[line.uuid] || 0;
            const amount = lineRemaining * ratio;
            const taxKey = ["ewallet", "gift_card"].includes(reward.program_id.program_type)
                ? line.tax_ids.map((t) => t.id)
                : line.tax_ids.filter((t) => t.amount_type !== "fixed").map((t) => t.id);

            discountable += amount;
            if (!discountablePerTax[taxKey]) {
                discountablePerTax[taxKey] = 0;
            }
            discountablePerTax[taxKey] += line.basePrice * ratio;
            qtyLeft -= qtyFromLine;
        }

        return { discountable, discountablePerTax };
    },
});
