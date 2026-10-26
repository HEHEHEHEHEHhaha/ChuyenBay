# Hướng Dẫn Chạy Dự Án FlightDelayML

Tài liệu này giải thích chi tiết ý nghĩa của các file trong dự án và thứ tự từng bước để khởi chạy chương trình.

---

## 📁 1. Cấu Trúc Dự Án & Ý Nghĩa Từng File

### 🔹 Các Thư Mục Chính
* **`data/`**: Chứa toàn bộ dữ liệu dự án.
  * `raw/`: Dữ liệu thô ban đầu (khi mới tải về).
  * `processed/`: Dữ liệu đã qua xử lý, làm sạch sẵn sàng để huấn luyện mô hình.
  * `external/`: Dữ liệu phụ từ bên ngoài (như dữ liệu thời tiết bổ sung).
* **`notebooks/`**: Chứa các file Jupyter Notebook (`.ipynb`) dùng để thử nghiệm, phân tích nhanh và vẽ đồ thị trực quan.
* **`src/`**: Thư mục mã nguồn chính (Source Code) chứa các script Python thực thi công việc.

---

### 🔹 Cấu Trúc Chi Tiết Các File Trong `src/`

1. **`download_data.py`**
   * **Ý nghĩa**: Tải tập dữ liệu chuyến bay gốc từ trên mạng (ví dụ: Kaggle hoặc nguồn open data) lưu vào thư mục `data/raw/`.
2. **`download_weather_csv.py`**
   * **Ý nghĩa**: Tải/thu thập dữ liệu thời tiết bổ sung lưu vào `data/external/` (thời tiết là yếu tố quan trọng ảnh hưởng tới hoãn chuyến bay).
<!-- 3. **`convert_to_csv.py`** -->
   * **Ý nghĩa**: Chuyển đổi định dạng dữ liệu (ví dụ: từ `.parquet` hoặc dạng nén khác sang `.csv`) hoặc lưu sang dạng chuẩn để dễ đọc và xử lý.
4. **`inspect_data.py`**
   * **Ý nghĩa**: Kiểm tra nhanh cấu trúc dữ liệu thô (xem kiểu dữ liệu, số hàng, số cột, kiểm tra giá trị trống/null).
5. **`eda_basic.py`**
   * **Ý nghĩa**: Thực hiện Khám phá Dữ liệu (Exploratory Data Analysis - EDA), tính toán các thông số thống kê cơ bản và trực quan hóa sự chậm trễ của các chuyến bay.

---

### 🔹 Các File Cấu Hình Ở Thư Mục Gốc
* **`.gitignore`**: Loại bỏ thư mục `.venv/` và `data/` khỏi Git để tránh đẩy file nặng (>100MB) lên GitHub làm lỗi repository.
* **`requirements.txt`**: Danh sách tất cả các thư viện Python cần thiết (như `pandas`, `numpy`, `matplotlib`, `scikit-learn`...).
* **`CachChay.md`**: File hướng dẫn sử dụng dự án này.

---

## 🚀 2. Thứ Tự Chạy Dự Án

Mở Terminal / Command Prompt tại thư mục gốc `FlightDelayML` và thực hiện theo từng bước sau:

### **Bước 1: Khởi tạo và kích hoạt môi trường ảo (nếu chưa làm)**
```bash
# Tạo môi trường ảo
python -m venv .venv

# Kích hoạt môi trường ảo (Windows)
.venv\Scripts\activate
```

### **Bước 2: Cài đặt các thư viện cần thiết**
```bash
pip install -r requirements.txt
```

### **Bước 3: Tải dữ liệu về dự án**
Chạy script để tải dữ liệu chuyến bay và dữ liệu thời tiết:
```bash
python src/download_data.py
python src/download_weather_csv.py
```

### **Bước 4: Chuyển đổi & Kiểm tra dữ liệu**
Chuyển đổi định dạng dữ liệu và kiểm tra cấu trúc ban đầu:
```bash
python src/convert_to_csv.py
python src/inspect_data.py
```

### **Bước 5: Phân tích khám phá dữ liệu (EDA)**
Chạy script phân tích tổng quan:
```bash
python src/eda_basic.py
```