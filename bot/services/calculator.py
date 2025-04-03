def calculate_customs(price_usd: float, engine: float, power: float, year: float) -> dict:
    euro_rate = 95  # Курс € к ₽ (актуальный)
    usd_rate = 90   # Курс $ к ₽
    price_rub = price_usd * usd_rate

    # 1. Пошлина (15% для авто до 3 лет)
    car_age = 2024 - year
    if car_age < 3:
        customs_duty = max(price_rub * 0.15, engine * 0.5 * euro_rate)
    else:
        customs_duty = max(price_rub * 0.2, engine * 0.7 * euro_rate)

    # 2. Акциз (ставки за л.с.)
    if power <= 90:
        excise = 0
    elif 90 < power <= 150:
        excise = 51 * power
    elif 150 < power <= 200:
        excise = 505 * power
    elif 200 < power <= 300:
        excise = 843 * power
    else:
        excise = 1420 * power

    # 3. НДС (20%)
    vat = (price_rub + customs_duty + excise) * 0.2

    # 4. Утильсбор
    recycling_fee = 34_000

    # 5. Доп. расходы (ЭРА-ГЛОНАСС, сертификация и т. д.)
    additional_costs = 70_000 + 50_000 + 40_000 + 50_000  # Примерные значения

    total = customs_duty + excise + vat + recycling_fee + additional_costs

    return {
        "price_rub": price_rub,
        "customs_duty": customs_duty,
        "excise": excise,
        "vat": vat,
        "recycling_fee": recycling_fee,
        "additional_costs": additional_costs,
        "total": total
    }