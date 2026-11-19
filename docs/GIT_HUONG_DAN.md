# Hướng dẫn Git nhanh cho nhóm

```bash
git clone <link-repo> && cd song-hong-ews
git checkout -b w2-clean-rules        # mỗi người 1 nhánh, đặt tên theo phần của mình
# ... sửa file của mình ...
git add src/ews/clean_rules.py
git commit -m "W2: thêm missing_report"
git push -u origin w2-clean-rules     # rồi mở Pull Request vào main
git pull origin main                  # lấy thay đổi của bạn khác trước khi làm tiếp
```
- Không `git add` file trong `data/`. CSV lớn trong `outputs/` chia sẻ qua Google Drive và ghi link vào sheet Interface_Files.
- Mỗi người chỉ sửa file module của mình nên gần như không xung đột.
