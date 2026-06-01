# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LoyaltyReward(models.Model):
    _inherit = "loyalty.reward"

    pos_block_promo = fields.Boolean(
        string="Aplicar por bloques completos en POS",
        help=(
            "Si está activo, el descuento de esta recompensa solo se aplicará a "
            "bloques completos de productos. Ejemplos: 2x1, 3x2, 6x5. "
            "Las unidades sobrantes quedan sin descuento."
        ),
    )
    pos_block_qty = fields.Integer(
        string="Cantidad del bloque",
        default=2,
        help="Cantidad total de productos que forman el bloque. Ejemplo: 2 para 2x1, 3 para 3x2.",
    )
    pos_block_pay_qty = fields.Integer(
        string="Cantidad a pagar",
        default=1,
        help="Cantidad de productos que se pagan dentro del bloque. Ejemplo: 1 para 2x1, 2 para 3x2.",
    )

    @api.constrains("pos_block_promo", "pos_block_qty", "pos_block_pay_qty", "reward_type", "discount_mode", "discount_applicability")
    def _check_pos_block_promo(self):
        for reward in self:
            if not reward.pos_block_promo:
                continue
            if reward.reward_type != "discount":
                raise ValidationError("La promoción por bloques solo está soportada para recompensas de tipo descuento.")
            if reward.discount_mode != "percent":
                raise ValidationError("La promoción por bloques solo está soportada con descuento porcentual.")
            if reward.discount_applicability != "specific":
                raise ValidationError("La promoción por bloques debe aplicarse a productos específicos.")
            if reward.pos_block_qty <= 1:
                raise ValidationError("La cantidad del bloque debe ser mayor a 1.")
            if reward.pos_block_pay_qty < 1:
                raise ValidationError("La cantidad a pagar debe ser mayor o igual a 1.")
            if reward.pos_block_pay_qty >= reward.pos_block_qty:
                raise ValidationError("La cantidad a pagar debe ser menor que la cantidad del bloque.")

    @api.onchange("pos_block_promo", "pos_block_qty", "pos_block_pay_qty", "discount_mode")
    def _onchange_pos_block_discount(self):
        for reward in self:
            if reward.pos_block_promo and reward.discount_mode == "percent" and reward.pos_block_qty:
                reward.discount = ((reward.pos_block_qty - reward.pos_block_pay_qty) / reward.pos_block_qty) * 100

    def write(self, vals):
        res = super().write(vals)
        fields_to_compute = {"pos_block_promo", "pos_block_qty", "pos_block_pay_qty", "discount_mode"}
        if fields_to_compute.intersection(vals):
            for reward in self.filtered(lambda r: r.pos_block_promo and r.discount_mode == "percent" and r.pos_block_qty):
                discount = ((reward.pos_block_qty - reward.pos_block_pay_qty) / reward.pos_block_qty) * 100
                super(LoyaltyReward, reward).write({"discount": discount})
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("pos_block_promo") and vals.get("discount_mode", "percent") == "percent":
                block_qty = vals.get("pos_block_qty") or 2
                pay_qty = vals.get("pos_block_pay_qty") or 1
                vals["discount"] = ((block_qty - pay_qty) / block_qty) * 100
        return super().create(vals_list)

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        fields_list += ["pos_block_promo", "pos_block_qty", "pos_block_pay_qty"]
        return fields_list
