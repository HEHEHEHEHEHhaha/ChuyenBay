import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import numpy as np
import pandas as pd
import os

# ============ BIẾN TOÀN CỤC ============
df = None
input_folder = ''
output_folder = ''
csv_files = []
conditions = []
delete_mode = None  # set sau khi tạo Tk


# ============ HÀM DÙNG CHUNG ============
def read_csv_safe(path):
    try:
        return pd.read_csv(path, encoding='utf-8')
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding='latin-1')


def load_folder():
    global df, input_folder, csv_files, conditions
    input_folder = filedialog.askdirectory(title='Chọn thư mục chứa các file CSV')
    if not input_folder:
        return
    try:
        csv_files = sorted([
            os.path.join(input_folder, f)
            for f in os.listdir(input_folder)
            if f.lower().endswith('.csv')
        ])
        if not csv_files:
            messagebox.showwarning('Cảnh báo', 'Không tìm thấy file CSV nào trong thư mục!')
            lbl_status.config(text='Không có file CSV', fg='red')
            return

        df = pd.read_csv(csv_files[0], encoding='utf-8', nrows=0)
        column_combobox['values'] = list(df.columns)
        if len(df.columns) > 0:
            column_combobox.set(df.columns[0])

        conditions.clear()
        update_condition_list()
        update_column_drop_list()

        lbl_status.config(
            text=f'Đã tải {len(csv_files)} file CSV | {len(df.columns)} cột',
            fg='green',
        )
        messagebox.showinfo(
            'Thành công',
            f'Tìm thấy {len(csv_files)} file CSV.\n'
            f'File mẫu: {os.path.basename(csv_files[0])}\n'
            f'Số cột: {len(df.columns)}',
        )
    except Exception as e:
        messagebox.showerror('Lỗi', f'Không thể đọc thư mục:\n{e}')


def choose_output_folder():
    global output_folder
    output_folder = filedialog.askdirectory(title='Chọn thư mục lưu kết quả')
    if output_folder:
        lbl_out_status.config(text=f'Lưu tại: {output_folder}', fg='green')


def _check_ready():
    if df is None or not csv_files:
        messagebox.showwarning('Cảnh báo', 'Vui lòng chọn thư mục CSV gốc trước!')
        return False
    if not output_folder:
        messagebox.showwarning('Cảnh báo', 'Vui lòng chọn thư mục lưu kết quả!')
        return False
    return True


def _process_all(process_fn):
    """Duyệt mọi file CSV. process_fn(df, fname) -> (df_result, extra_dict)."""
    total_files = 0
    total_initial = 0
    total_removed = 0
    failed = []
    same_folder = os.path.abspath(input_folder) == os.path.abspath(output_folder)
    extra_total = {}

    for fp in csv_files:
        fname = os.path.basename(fp)
        try:
            current_df = read_csv_safe(fp)
            initial_rows = len(current_df)
            result_df, extra = process_fn(current_df, fname)
            removed = initial_rows - len(result_df)

            out_name = fname
            if same_folder:
                name, ext = os.path.splitext(fname)
                out_name = f'{name}_processed{ext}'
            out_path = os.path.join(output_folder, out_name)
            result_df.to_csv(out_path, index=False, encoding='utf-8')

            total_files += 1
            total_initial += initial_rows
            total_removed += removed
            for k, v in extra.items():
                extra_total[k] = extra_total.get(k, 0) + v
        except Exception as e:
            failed.append(f'• {fname}: {e}')

    return {
        'total_files': total_files,
        'total_initial': total_initial,
        'total_removed': total_removed,
        'failed': failed,
        'extra': extra_total,
        'same_folder': same_folder,
    }


def _show_result(stats, title, extra_lines=''):
    msg = f'Đã xử lý thành công {stats["total_files"]}/{len(csv_files)} file.\n\n'
    msg += f'- Tổng dòng ban đầu: {stats["total_initial"]:,}\n'
    if extra_lines:
        msg += extra_lines
    msg += f'\nĐã lưu tại:\n{output_folder}'
    if stats['same_folder']:
        msg += '\n\n(File kết quả có hậu tố "_processed" do trùng thư mục gốc)'
    if stats['failed']:
        msg += f'\n\n⚠ File lỗi ({len(stats["failed"])}):\n' + '\n'.join(stats['failed'][:10])
        if len(stats['failed']) > 10:
            msg += f'\n... và {len(stats["failed"]) - 10} file khác'
        messagebox.showwarning(f'{title} (có lỗi)', msg)
    else:
        messagebox.showinfo(title, msg)


# ============ TAB 1: LỌC DÒNG ============
def add_condition():
    global conditions
    if df is None:
        messagebox.showwarning('Cảnh báo', 'Vui lòng chọn thư mục CSV trước!')
        return

    col = column_combobox.get()
    val_input = entry_value.get().strip()

    if not col:
        messagebox.showwarning('Cảnh báo', 'Vui lòng chọn trường (cột)!')
        return

    is_null_cond = (
        val_input == ''
        or val_input.lower() in ['null', 'rỗng', 'trong', 'nan', 'none']
    )

    if is_null_cond:
        conditions.append({
            'col': col, 'type': 'null',
            'display': f'Cột [{col}] là Rỗng (NaN/Null)',
        })
    else:
        try:
            val = float(val_input) if '.' in val_input else int(val_input)
        except ValueError:
            val = val_input
        conditions.append({
            'col': col, 'type': 'value', 'val': val,
            'display': f'Cột [{col}] == {val}',
        })

    update_condition_list()
    entry_value.delete(0, tk.END)


def remove_selected_condition():
    sel = listbox_conditions.curselection()
    if not sel:
        messagebox.showwarning('Cảnh báo', 'Vui lòng chọn một điều kiện để xóa!')
        return
    conditions.pop(sel[0])
    update_condition_list()


def update_condition_list():
    listbox_conditions.delete(0, tk.END)
    for i, cond in enumerate(conditions):
        listbox_conditions.insert(tk.END, f'Điều kiện {i+1}: {cond["display"]}')


def execute_filter_rows():
    if not _check_ready():
        return
    if not conditions:
        messagebox.showwarning('Cảnh báo', 'Vui lòng thêm ít nhất một điều kiện lọc!')
        return

    def process(current_df, fname):
        remove_mask = np.zeros(len(current_df), dtype=bool)
        for cond in conditions:
            col = cond['col']
            if col not in current_df.columns:
                raise ValueError(f'Thiếu cột [{col}]')
            if cond['type'] == 'null':
                m = current_df[col].isna() | (current_df[col].astype(str).str.strip() == '')
            else:
                m = current_df[col] == cond['val']
            remove_mask = remove_mask | m
        return current_df[~remove_mask], {}

    stats = _process_all(process)
    extra = (
        f'- Đã xóa: {stats["total_removed"]:,} dòng\n'
        f'- Còn lại: {stats["total_initial"] - stats["total_removed"]:,} dòng\n'
    )
    _show_result(stats, 'Hoàn tất lọc dòng', extra)


# ============ TAB 2: XÓA CỘT ============
def update_column_drop_list():
    listbox_drop_cols.delete(0, tk.END)
    if df is None:
        return
    for col in df.columns:
        listbox_drop_cols.insert(tk.END, col)


def select_all_columns():
    if listbox_drop_cols.size() > 0:
        listbox_drop_cols.selection_set(0, tk.END)


def deselect_all_columns():
    listbox_drop_cols.selection_clear(0, tk.END)


def on_mode_change(*args):
    if delete_mode.get() == 'selected':
        lbl_mode_hint.config(
            text='👉 Đang chọn cột MUỐN XÓA — các cột KHÔNG chọn sẽ được giữ lại',
            fg='#d32f2f',
        )
    else:
        lbl_mode_hint.config(
            text='👉 Đang chọn cột MUỐN GIỮ — tất cả cột KHÔNG chọn sẽ bị xóa',
            fg='#2e7d32',
        )


def execute_delete_columns():
    if not _check_ready():
        return

    mode = delete_mode.get()
    selected = [listbox_drop_cols.get(i) for i in listbox_drop_cols.curselection()]
    all_cols = list(df.columns) if df is not None else []

    if not all_cols:
        messagebox.showwarning('Cảnh báo', 'Chưa có danh sách cột!')
        return

    if mode == 'selected':
        if not selected:
            messagebox.showwarning('Cảnh báo', 'Vui lòng chọn ít nhất một cột để xóa!')
            return
        if len(selected) == len(all_cols):
            if not messagebox.askyesno(
                'Xác nhận',
                f'Bạn đang chọn XÓA TẤT CẢ {len(all_cols)} cột.\n'
                'File kết quả sẽ KHÔNG còn cột dữ liệu nào. Tiếp tục?'
            ):
                return
        to_delete = selected
        mode_label = f'Xóa {len(to_delete)} cột đã chọn'
    else:  # unselected
        if not selected:
            if not messagebox.askyesno(
                'Xác nhận',
                'Bạn chưa chọn cột nào.\n'
                'Điều này sẽ XÓA TẤT CẢ cột. Tiếp tục?'
            ):
                return
            to_delete = all_cols
        else:
            if len(selected) == len(all_cols):
                messagebox.showinfo(
                    'Thông báo',
                    'Bạn đã chọn tất cả cột — không có cột nào cần xóa.'
                )
                return
            to_delete = [c for c in all_cols if c not in selected]
        mode_label = f'Giữ {len(selected)} cột đã chọn — xóa {len(to_delete)} cột còn lại'

    def process(current_df, fname):
        existing = [c for c in to_delete if c in current_df.columns]
        result = current_df.drop(columns=existing) if existing else current_df.copy()
        return result, {'Cột đã xóa': len(existing)}

    stats = _process_all(process)
    extra = f'- {mode_label}\n'
    _show_result(stats, 'Hoàn tất xóa cột', extra)


# ============ GIAO DIỆN CHÍNH ============
root = tk.Tk()
root.title('Xử Lý Dữ Liệu CSV Theo Thư Mục')
root.geometry('700x730')
root.resizable(False, False)

tk.Label(
    root, text='XỬ LÝ DỮ LIỆU CSV THEO THƯ MỤC',
    font=('Arial', 13, 'bold'), fg='#333333',
).pack(pady=8)

# --- Khung chọn thư mục (dùng chung) ---
frame_file = tk.Frame(root)
frame_file.pack(pady=3, padx=20, fill='x')
tk.Button(
    frame_file, text='1. Chọn thư mục CSV gốc',
    command=load_folder, bg='#4CAF50', fg='white',
    font=('Arial', 10, 'bold'), width=22,
).pack(side='left')
lbl_status = tk.Label(
    frame_file, text='Chưa chọn thư mục nào',
    font=('Arial', 9), fg='gray',
)
lbl_status.pack(side='left', padx=10)

frame_out = tk.Frame(root)
frame_out.pack(pady=3, padx=20, fill='x')
tk.Button(
    frame_out, text='2. Chọn thư mục lưu kết quả',
    command=choose_output_folder, bg='#009688', fg='white',
    font=('Arial', 10, 'bold'), width=22,
).pack(side='left')
lbl_out_status = tk.Label(
    frame_out, text='Chưa chọn thư mục lưu',
    font=('Arial', 9), fg='gray',
)
lbl_out_status.pack(side='left', padx=10)

# --- Notebook với 2 tab ---
notebook = ttk.Notebook(root)
notebook.pack(fill='both', expand=True, padx=15, pady=10)

# ===== TAB 1: Lọc dòng =====
tab_filter = tk.Frame(notebook)
notebook.add(tab_filter, text='  📋  Tab 1: Lọc dòng theo điều kiện  ')

frame_add = tk.LabelFrame(
    tab_filter, text=' Thêm điều kiện lọc (Cột & Giá trị hoặc Rỗng) ',
    font=('Arial', 10, 'bold'),
)
frame_add.pack(pady=8, padx=10, fill='x', ipadx=10, ipady=5)

f_col = tk.Frame(frame_add)
f_col.pack(fill='x', pady=5)
tk.Label(f_col, text='Chọn trường (cột):', width=16, anchor='w').pack(side='left')
column_combobox = ttk.Combobox(f_col, state='readonly', width=32)
column_combobox.pack(side='left', padx=5)

f_val = tk.Frame(frame_add)
f_val.pack(fill='x', pady=5)
tk.Label(f_val, text='Nhập giá trị xóa:', width=16, anchor='w').pack(side='left')
entry_value = tk.Entry(f_val, font=('Arial', 10), width=34)
entry_value.pack(side='left', padx=5)

tk.Label(
    frame_add,
    text='💡 Nhập số/chữ (vd: 1) HOẶC gõ "NULL"/để trống để xóa dòng bị rỗng',
    font=('Arial', 8, 'italic'), fg='#d32f2f',
).pack(anchor='w', padx=115, pady=2)

tk.Button(
    frame_add, text='+ Thêm điều kiện này vào danh sách',
    command=add_condition, bg='#FF9800', fg='white',
    font=('Arial', 9, 'bold'),
).pack(pady=8)

frame_cond = tk.LabelFrame(
    tab_filter, text=' Danh sách điều kiện (Xóa dòng nếu thỏa BẤT KỲ điều kiện nào) ',
    font=('Arial', 10, 'bold'),
)
frame_cond.pack(pady=5, padx=10, fill='both', expand=True, ipadx=5, ipady=5)

listbox_conditions = tk.Listbox(frame_cond, font=('Arial', 9), height=7)
listbox_conditions.pack(fill='both', expand=True, padx=5, pady=5)

tk.Button(
    frame_cond, text='Xóa điều kiện đã chọn',
    command=remove_selected_condition,
    bg='#f44336', fg='white', font=('Arial', 9, 'bold'),
).pack(pady=5, padx=5, fill='x')

tk.Button(
    tab_filter, text='▶ THỰC THI LỌC DÒNG',
    command=execute_filter_rows,
    bg='#2196F3', fg='white', font=('Arial', 11, 'bold'),
).pack(pady=12, fill='x', padx=10)

# ===== TAB 2: Xóa cột =====
tab_delete = tk.Frame(notebook)
notebook.add(tab_delete, text='  🗑  Tab 2: Xóa cột  ')

delete_mode = tk.StringVar(value='selected')

frame_mode = tk.LabelFrame(
    tab_delete, text=' Chế độ xóa ',
    font=('Arial', 10, 'bold'),
)
frame_mode.pack(pady=8, padx=10, fill='x', ipadx=10, ipady=5)

tk.Radiobutton(
    frame_mode, text='🔴  Xóa các cột ĐÃ CHỌN  (giữ các cột không chọn)',
    variable=delete_mode, value='selected',
    font=('Arial', 10), command=on_mode_change,
).pack(anchor='w', padx=15, pady=4)

tk.Radiobutton(
    frame_mode, text='🟢  Xóa các cột KHÔNG CHỌN  (chỉ giữ các cột đã chọn)',
    variable=delete_mode, value='unselected',
    font=('Arial', 10), command=on_mode_change,
).pack(anchor='w', padx=15, pady=4)

lbl_mode_hint = tk.Label(
    tab_delete, text='',
    font=('Arial', 9, 'italic'), fg='#d32f2f',
)
lbl_mode_hint.pack(pady=3)

frame_cols = tk.LabelFrame(
    tab_delete, text=' Danh sách cột (Ctrl+Click / Shift+Click để chọn nhiều) ',
    font=('Arial', 10, 'bold'),
)
frame_cols.pack(pady=5, padx=10, fill='both', expand=True, ipadx=5, ipady=5)

listbox_drop_cols = tk.Listbox(
    frame_cols, font=('Arial', 9), height=10,
    selectmode=tk.MULTIPLE, exportselection=False,
)
listbox_drop_cols.pack(fill='both', expand=True, padx=5, pady=5)

frame_col_btns = tk.Frame(frame_cols)
frame_col_btns.pack(pady=5, padx=5, fill='x')
tk.Button(
    frame_col_btns, text='Chọn tất cả', command=select_all_columns,
    bg='#607D8B', fg='white', font=('Arial', 9),
).pack(side='left', fill='x', expand=True, padx=(0, 3))
tk.Button(
    frame_col_btns, text='Bỏ chọn tất cả', command=deselect_all_columns,
    bg='#9E9E9E', fg='white', font=('Arial', 9),
).pack(side='left', fill='x', expand=True, padx=(3, 0))

tk.Button(
    tab_delete, text='▶ THỰC THI XÓA CỘT',
    command=execute_delete_columns,
    bg='#e91e63', fg='white', font=('Arial', 11, 'bold'),
).pack(pady=12, fill='x', padx=10)

# Khởi tạo hint lúc mở
on_mode_change()

root.mainloop()