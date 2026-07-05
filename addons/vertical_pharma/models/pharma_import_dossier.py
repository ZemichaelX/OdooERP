# -*- coding: utf-8 -*-
"""Import shipment dossier: one record per import file, tying the supplier,
ETA, clearance paperwork (chatter attachments) and landed costs to the
receipts — and through them to every batch. This is the importer's
batch ↔ import-file traceability the DAT proposal asks for."""

from odoo import api, fields, models


class PharmaImportDossier(models.Model):
    _name = "pharma.import.dossier"
    _description = "Pharma Import Shipment Dossier"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "eta_date desc, id desc"

    name = fields.Char(
        required=True,
        copy=False,
        default=lambda self: self.env._("New"),
        tracking=True,
        help="Import file reference. Auto-numbered (IMP/...) when left as 'New'.",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    supplier_id = fields.Many2one(
        "res.partner",
        required=True,
        tracking=True,
        help="The foreign manufacturer or trading house shipping this file.",
    )
    eta_date = fields.Date(
        string="ETA",
        tracking=True,
        help="Estimated arrival at the port of entry / bonded warehouse.",
    )
    status = fields.Selection(
        selection=[
            ("in_transit", "In Transit"),
            ("customs", "In Customs"),
            ("received", "Received"),
        ],
        default="in_transit",
        required=True,
        tracking=True,
    )
    note = fields.Text(
        string="Clearance Notes",
        help="Clearance milestones; attach the paperwork (BL, packing list, "
        "EFDA import permit, customs declaration) in the chatter.",
    )
    amount_goods = fields.Monetary(string="Goods Value", tracking=True)
    amount_freight = fields.Monetary(string="Freight & Insurance")
    amount_customs = fields.Monetary(string="Customs Duty & Taxes")
    amount_clearance = fields.Monetary(string="Clearance & Handling")
    amount_total = fields.Monetary(
        string="Total Landed Cost",
        compute="_compute_amount_total",
        store=True,
        help="Goods + freight/insurance + customs + clearance.",
    )
    picking_ids = fields.One2many(
        "stock.picking",
        "pharma_dossier_id",
        string="Receipts",
        help="Warehouse receipts that brought this import file in.",
    )
    lot_ids = fields.Many2many(
        "stock.lot",
        string="Batches",
        compute="_compute_lot_ids",
        help="Every batch received under this import file.",
    )
    lot_count = fields.Integer(compute="_compute_lot_ids")

    @api.depends("amount_goods", "amount_freight", "amount_customs", "amount_clearance")
    def _compute_amount_total(self):
        """Sum the landed-cost components."""
        for dossier in self:
            dossier.amount_total = (
                dossier.amount_goods
                + dossier.amount_freight
                + dossier.amount_customs
                + dossier.amount_clearance
            )

    @api.depends("picking_ids.move_line_ids.lot_id")
    def _compute_lot_ids(self):
        """Batches are derived from the linked receipts' move lines."""
        for dossier in self:
            dossier.lot_ids = dossier.picking_ids.move_line_ids.lot_id
            dossier.lot_count = len(dossier.lot_ids)

    @api.model_create_multi
    def create(self, vals_list):
        """Assign the IMP/ sequence to dossiers left on the 'New' default."""
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == self.env._("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("pharma.import.dossier") or "/"
                )
        return super().create(vals_list)

    def action_view_lots(self):
        """Open the batches received under this import file."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Batches — %(dossier)s", dossier=self.name),
            "res_model": "stock.lot",
            "view_mode": "list,form",
            "domain": [("id", "in", self.lot_ids.ids)],
        }
