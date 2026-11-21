"""Mock Geography lessons. ALL NUMBERS ARE FICTIONAL: every source is labelled DỮ LIỆU MINH HỌA."""

from typing import Any

NOTE = "DỮ LIỆU MINH HỌA"

LESSONS: list[dict[str, Any]] = [
    {
        "key": "dan-so-vung", "grade": 10, "author": "gv.dia", "visibility": "SCHOOL", "publish": True,
        "title": "Phân bố dân cư theo vùng",
        "goal": "Đọc và so sánh số dân giữa các vùng từ bảng số liệu.",
        "heading": f"Số dân các vùng năm 2020 ({NOTE})",
        "paras": [
            f"Dân cư nước ta phân bố không đều giữa các vùng kinh tế ({NOTE}).",
            "Năm 2020, số dân giữa các vùng có sự chênh lệch đáng kể, phản ánh điều kiện tự nhiên và kinh tế khác nhau.",
        ],
        "ent": "Vùng", "metric": "số dân", "unit": "triệu người", "period": "2020", "area": None,
        "rows": [("Trung du và miền núi phía Bắc", "12,6"), ("Tây Nguyên", "5,9"),
                 ("Đồng bằng sông Hồng", "23,2"), ("Đông Nam Bộ", "17,8")],
    },
    {
        "key": "dien-tich-rung", "grade": 10, "author": "gv.dia", "visibility": "PRIVATE", "publish": False,
        "title": "Tài nguyên rừng ở các vùng",
        "goal": "So sánh diện tích rừng và rút ra nhận xét về độ che phủ.",
        "heading": f"Diện tích rừng các vùng năm 2021 ({NOTE})",
        "paras": [
            f"Rừng là tài nguyên quan trọng góp phần bảo vệ môi trường ({NOTE}).",
            "Năm 2021, diện tích rừng phân bố không đều giữa các vùng, phụ thuộc vào địa hình và mật độ dân cư.",
        ],
        "ent": "Vùng", "metric": "diện tích rừng", "unit": "nghìn ha", "period": "2021", "area": None,
        "rows": [("Bắc Trung Bộ", "3.120,5"), ("Trung du và miền núi phía Bắc", "4.015,8"),
                 ("Tây Nguyên", "2.560,3"), ("Đông Nam Bộ", "480,2")],
    },
    {
        "key": "san-luong-lua", "grade": 10, "author": "gv.dia", "visibility": "PRIVATE", "publish": False,
        "title": "Sản xuất lúa gạo theo vùng",
        "goal": "Đọc bảng sản lượng lúa và tính chênh lệch giữa các vùng.",
        "heading": f"Sản lượng lúa các vùng năm 2022 ({NOTE})",
        "paras": [
            f"Lúa là cây lương thực chính của nước ta ({NOTE}).",
            "Năm 2022, sản lượng lúa khác nhau giữa các vùng, phụ thuộc vào đất đai, nguồn nước và tập quán canh tác.",
        ],
        "ent": "Vùng", "metric": "sản lượng lúa", "unit": "nghìn tấn", "period": "2022", "area": None,
        "rows": [("Đồng bằng sông Hồng", "6.080,2"), ("Bắc Trung Bộ", "4.310,7"),
                 ("Tây Nguyên", "1.150,9"), ("Đồng bằng sông Cửu Long", "24.350,5")],
    },
    {
        "key": "gdp-nganh", "grade": 11, "author": "gv.dia", "visibility": "PRIVATE", "publish": False,
        "title": "Cơ cấu GDP theo nhóm ngành",
        "goal": "Đọc cơ cấu GDP và nhận xét chuyển dịch kinh tế.",
        "heading": f"Cơ cấu GDP theo nhóm ngành năm 2020 ({NOTE})",
        "paras": [
            f"Cơ cấu kinh tế phản ánh trình độ phát triển của một quốc gia ({NOTE}).",
            "Năm 2020, cơ cấu GDP phản ánh vai trò khác nhau của từng nhóm ngành trong nền kinh tế.",
        ],
        "ent": "Nhóm ngành", "metric": "tỉ trọng GDP", "unit": "%", "period": "2020", "area": "Việt Nam",
        "rows": [("Dịch vụ", "42,8"), ("Công nghiệp và xây dựng", "37,6"),
                 ("Nông, lâm, thủy sản", "11,9"), ("Thuế sản phẩm trừ trợ cấp", "7,7")],
    },
    {
        "key": "san-luong-dien", "grade": 11, "author": "gv.dia", "visibility": "PRIVATE", "publish": False,
        "title": "Sản lượng điện theo nguồn",
        "goal": "So sánh sản lượng điện giữa các nguồn phát điện.",
        "heading": f"Sản lượng điện theo nguồn năm 2021 ({NOTE})",
        "paras": [
            f"Điện là ngành năng lượng nền tảng của công nghiệp ({NOTE}).",
            "Năm 2021, sản lượng điện của các nguồn phát có sự khác biệt do đặc điểm tài nguyên và công nghệ.",
        ],
        "ent": "Nguồn điện", "metric": "sản lượng điện", "unit": "tỉ kWh", "period": "2021", "area": "Việt Nam",
        "rows": [("Thủy điện", "81,5"), ("Nhiệt điện khí", "29,8"),
                 ("Nhiệt điện than", "97,3"), ("Năng lượng tái tạo", "34,2")],
    },
    {
        "key": "xuat-khau", "grade": 11, "author": "gv.khac", "visibility": "PRIVATE", "publish": False,
        "title": "Xuất khẩu hàng hóa chủ lực",
        "goal": "Đọc bảng kim ngạch xuất khẩu và tính chênh lệch giữa các nhóm hàng.",
        "heading": f"Kim ngạch xuất khẩu theo nhóm hàng năm 2022 ({NOTE})",
        "paras": [
            f"Xuất khẩu là động lực quan trọng của tăng trưởng kinh tế ({NOTE}).",
            "Năm 2022, kim ngạch xuất khẩu giữa các nhóm hàng có sự chênh lệch rõ rệt.",
        ],
        "ent": "Nhóm hàng", "metric": "kim ngạch xuất khẩu", "unit": "tỉ USD", "period": "2022",
        "area": "Việt Nam",
        "rows": [("Dệt may", "37,6"), ("Điện tử và linh kiện", "55,4"),
                 ("Giày dép", "26,9"), ("Thủy sản", "11,0")],
    },
]
