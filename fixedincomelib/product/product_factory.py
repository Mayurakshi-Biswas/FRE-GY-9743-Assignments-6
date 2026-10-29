"""Convention-driven factory adapted from the instructor template.

Swap axis1 is tenor or start-offset x tenor. FRA uses start-offset x end-offset,
with both offsets measured from value_date, or two explicit ISO dates.
"""

from typing import Any
from fixedincomelib.date import Date, TermOrDate, add_period
from fixedincomelib.market.data_conventions import (
    CompoundingMethod, DataConvention, DataConventionFRA,
    DataConventionRFRSwap, DataConventionOvernightIndexBasisSwap,
)
from fixedincomelib.product.product_interfaces import ProductBuilderRegistry
from fixedincomelib.product.linear_products import ProductFRA, ProductRFRSwap, ProductOvernightIndexBasisSwap
from fixedincomelib.product.utilities import PayOrReceive


class ProductFactory:
    @classmethod
    def create_product_from_data_convention(
        cls,
        value_date: Date,
        axis1: str,
        data_convention: DataConvention,
        values: float,
        **kwargs: Any,
    ):

        convention_obj: DataConvention = data_convention
        prod_type = convention_obj.type()
        func = ProductBuilderRegistry().get(prod_type)
        return func(value_date, axis1, convention_obj, values, **kwargs)

    @classmethod
    def create_rfr_swap(
        cls,
        value_date: Date,
        axis1: str,
        data_convention: DataConventionRFRSwap,
        values: float,
        **kwargs: Any,
    ) -> ProductRFRSwap:

        # ---------------- TODO 3 ----------------
        # Split axis1 into (start, end). end is None for a spot swap like "1Y".
        first, second = cls._tokenize_axis1(axis1)
        bdc = data_convention.business_day_convention
        holidays = data_convention.holiday_convention

        if second is None:
            # "1Y": spot-starting, run for the given tenor.
            effective_date = value_date
            term_or_termination_date = first
        else:
            # "3Mx1Y": start = value_date + 3M; "2026-04-02x...": explicit start.
            if first.is_term():
                effective_date = add_period(value_date, first.get_term(), bdc, holidays)
            else:
                effective_date = first.get_date()
            # Second token is a tenor from the start, or an explicit end date.
            term_or_termination_date = second

        return ProductRFRSwap(
            effective_date,
            term_or_termination_date,
            data_convention.payment_offset,                              # payment_off_set
            data_convention.index_str,                                   # on_index
            values,                                                      # fixed_rate = quote
            PayOrReceive.from_string(kwargs.get("pay_or_rec", "receive")),
            kwargs.get("notional", 1e4),
            data_convention.acc_period,                                  # fixed accrual period
            data_convention.acc_basis,                                   # accrual basis
            data_convention.acc_period,                                  # floating accrual period
            bdc,                                                         # pay BDC
            holidays,                                                    # pay holidays
            0.0,                                                         # spread
            data_convention.compounding_method,
        )
        # ----------------------------------------

    @classmethod
    def create_overnight_index_basis_swap(
        cls,
        value_date: Date,
        axis1: str,
        data_convention: DataConventionOvernightIndexBasisSwap,
        values: float,
        **kwargs: Any,
    ) -> ProductOvernightIndexBasisSwap:

        # ---------------- TODO 4 ----------------
        # Same swap date rules as create_rfr_swap.
        first, second = cls._tokenize_axis1(axis1)
        bdc = data_convention.business_day_convention
        holidays = data_convention.holiday_convention

        if second is None:
            effective_date = value_date
            term_or_termination_date = first
        else:
            if first.is_term():
                effective_date = add_period(value_date, first.get_term(), bdc, holidays)
            else:
                effective_date = first.get_date()
            term_or_termination_date = second

        return ProductOvernightIndexBasisSwap(
            effective_date,
            term_or_termination_date,
            data_convention.payment_offset,                              # payment_off_set
            data_convention.index_1_str,                                 # leg 1 index (BASIS_OI_INDEX)
            data_convention.index_2_str,                                 # leg 2 index (REFERENCE_OI_INDEX)
            values,                                                      # quote = spread over leg 1
            PayOrReceive.from_string(kwargs.get("pay_or_rec", "receive")),
            kwargs.get("notional", 1e4),
            data_convention.acc_period_1,                                # leg 1 accrual period
            data_convention.acc_basis,                                   # accrual basis
            data_convention.acc_period_2,                                # leg 2 accrual period
            bdc,                                                         # pay BDC
            holidays,                                                    # pay holidays
            data_convention.compounding_method,
        )
        # ----------------------------------------

    @classmethod
    def create_fra(cls, value_date, axis1, data_convention, values, **kwargs):
        start, end = cls._tokenize_axis1(axis1)
        bdc = data_convention.business_day_convention
        holidays = data_convention.holiday_convention
        if start.is_term():
            effective_date = add_period(value_date, start.get_term(), bdc, holidays)
            termination_date = add_period(value_date, end.get_term(), bdc, holidays)
        else:
            effective_date = start.get_date()
            termination_date = end.get_date()
        return ProductFRA(
            effective_date, TermOrDate(termination_date), data_convention.index_str,
            values, PayOrReceive.from_string(kwargs.get("pay_or_rec", "receive")),
            kwargs.get("notional", 1e4), data_convention.acc_basis, bdc, holidays,
        )

    @staticmethod
    def _tokenize_axis1(axis1):
        tokens = axis1.strip().replace("X", "x").split("x")
        first = TermOrDate(tokens[0].strip())
        second = TermOrDate(tokens[1].strip()) if len(tokens) == 2 else None
        return first, second


ProductBuilderRegistry().register(DataConventionFRA.type(), ProductFactory.create_fra)
ProductBuilderRegistry().register(DataConventionRFRSwap.type(), ProductFactory.create_rfr_swap)
ProductBuilderRegistry().register(DataConventionOvernightIndexBasisSwap.type(),
                                  ProductFactory.create_overnight_index_basis_swap)