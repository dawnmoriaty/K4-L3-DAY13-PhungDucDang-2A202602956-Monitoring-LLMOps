from app.pii import scrub_text


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_common_vietnamese_phone_formats() -> None:
    phone_numbers = (
        "0901234567",
        "090 123 4567",
        "090.123.4567",
        "090-123-4567",
        "+84 90 123 4567",
    )

    for phone_number in phone_numbers:
        out = scrub_text(f"Contact: {phone_number}")
        assert phone_number not in out
        assert "REDACTED_PHONE_VN" in out


def test_scrub_cccd() -> None:
    cccds = ("001201012345", "079099123456")
    for cccd in cccds:
        out = scrub_text(f"So CCCD la {cccd}")
        assert cccd not in out
        assert "REDACTED_CCCD" in out


def test_scrub_credit_card() -> None:
    cards = (
        "4111 1111 1111 1111",
        "4111-1111-1111-1111",
        "4111111111111111",
    )
    for card in cards:
        out = scrub_text(f"Card number: {card}")
        assert card not in out
        assert "REDACTED_CREDIT_CARD" in out


def test_scrub_passport() -> None:
    passports = ("B1234567", "C87654321")
    for passport in passports:
        out = scrub_text(f"Passport number: {passport}")
        assert passport not in out
        assert "REDACTED_PASSPORT" in out


def test_scrub_address_vn() -> None:
    addresses = (
        "Số 123 đường Nguyễn Trãi, Phường 2, Quận 5, TP.HCM",
        "ngõ 45 phố Tây Sơn, quận Đống Đa, Hà Nội",
        "Số 1 đường Đại Cồ Việt, phường Bách Khoa, quận Hai Bà Trưng, thành phố Hà Nội",
    )
    for addr in addresses:
        out = scrub_text(f"Dia chi cua toi: {addr}")
        assert addr not in out
        assert "REDACTED_ADDRESS_VN" in out


def test_scrub_address_vn_variations() -> None:
    variations = (
        "so 123 duong nguyen trai, phuong 2, quan 5, tp hcm",
        "SO 123 DUONG NGUYEN TRAI, PHUONG 2, QUAN 5, TPHCM",
        "so 123 duong nguyen trai p.2 q.5 tp.hcm",
        "Số 123 Đường Nguyễn Trãi, Phường 2, Quận 5, TP.HCM",
        "Địa chỉ: 12/3A Lê Lợi, P. Bến Nghé, Q.1",
        "đ/c: số 5 phố Huế, Hà Nội",
        "DC: 45 Nguyen Hue, Q1, HCM",
        "nơi ở: 12 pho Hue, Ha Noi",
    )
    for addr in variations:
        out = scrub_text(f"Lien he: {addr}")
        assert addr not in out
        assert "REDACTED_ADDRESS_VN" in out


def test_scrub_case_insensitivity() -> None:
    out_email = scrub_text("Email: STUDENT@VINUNI.EDU.VN")
    assert "STUDENT@VINUNI.EDU.VN" not in out_email
    assert "REDACTED_EMAIL" in out_email

    out_passport = scrub_text("Passport: b1234567")
    assert "b1234567" not in out_passport
    assert "REDACTED_PASSPORT" in out_passport



