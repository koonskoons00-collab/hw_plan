import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime


class AssignmentDialog(tk.Toplevel):
    def __init__(self, parent, manager, item=None, default_date=None, on_success=None):
        super().__init__(parent)
        self.manager = manager
        self.item = item
        self.on_success = on_success
        self.title("과제 수정" if item else "새 과제 추가")
        self.geometry("380x280")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        today_str = default_date or datetime.now().strftime("%Y-%m-%d")
        fields = [
            ("과목명:", "entry_subject", item.subject if item else ""),
            ("과제명:", "entry_title", item.title if item else ""),
            ("마감 날짜 (YYYY-MM-DD):", "entry_date", item.due_date if item else today_str),
            ("마감 시간 (HH:MM):", "entry_time", item.due_time if item else "23:59"),
        ]

        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        self.entries = {}
        for row, (label, key, val) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky=tk.W, pady=4)
            ent = ttk.Entry(frame, width=28)
            ent.insert(0, val)
            ent.grid(row=row, column=1, sticky=tk.EW, pady=4)
            self.entries[key] = ent

        btn_box = ttk.Frame(frame)
        btn_box.grid(row=len(fields), column=0, columnspan=2, pady=15)
        ttk.Button(btn_box, text="저장", command=self._save, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_box, text="취소", command=self.destroy, width=10).pack(side=tk.LEFT, padx=5)
        self.entries["entry_subject"].focus_set()

    def _save(self):
        subj = self.entries["entry_subject"].get().strip()
        title = self.entries["entry_title"].get().strip()
        date_str = self.entries["entry_date"].get().strip()
        time_str = self.entries["entry_time"].get().strip() or "23:59"

        if not subj or not title:
            messagebox.showwarning("입력 오류", "과목명과 과제명을 모두 입력해주세요.", parent=self)
            return

        try:
            datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        except ValueError:
            messagebox.showerror(
                "날짜/시간 오류",
                "날짜는 YYYY-MM-DD (예: 2026-10-15),\n시간은 HH:MM (예: 23:59) 형식이어야 합니다.",
                parent=self,
            )
            return

        if self.item:
            self.manager.update(self.item.id, subj, title, date_str, time_str)
        else:
            self.manager.add(subj, title, date_str, time_str)

        if self.on_success:
            self.on_success()
        self.destroy()


class CompletedDialog(tk.Toplevel):
    def __init__(self, parent, manager, on_refresh=None):
        super().__init__(parent)
        self.manager = manager
        self.on_refresh = on_refresh
        self.title("완료된 과제 보관함")
        self.geometry("620x350")
        self.transient(parent)
        self.grab_set()

        ttk.Label(self, text="✔️ 완료 처리된 과제 목록", font=("맑은 고딕", 11, "bold")).pack(
            pady=(10, 5)
        )

        cols = ("subject", "title", "due")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=9)
        self.tree.heading("subject", text="과목명")
        self.tree.heading("title", text="과제명")
        self.tree.heading("due", text="마감 일시")
        self.tree.column("subject", width=140, anchor=tk.W)
        self.tree.column("title", width=300, anchor=tk.W)
        self.tree.column("due", width=140, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=(10, 0), pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, before=self.tree)

        btn_box = ttk.Frame(self, padding=8)
        btn_box.pack(fill=tk.X)
        ttk.Button(btn_box, text="미완료로 복원", command=self._restore).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_box, text="영구 삭제", command=self._delete).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_box, text="닫기", command=self.destroy).pack(side=tk.RIGHT, padx=5)

        self._populate()

    def _populate(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for a in self.manager.get_completed():
            self.tree.insert(
                "",
                tk.END,
                iid=str(a.id),
                values=(a.subject, a.title, f"{a.due_date} {a.due_time}"),
            )

    def _get_selected_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("안내", "과제를 선택해주세요.", parent=self)
            return None
        return int(sel[0])

    def _restore(self):
        item_id = self._get_selected_id()
        if item_id:
            self.manager.toggle_complete(item_id)
            self._populate()
            if self.on_refresh:
                self.on_refresh()

    def _delete(self):
        item_id = self._get_selected_id()
        if item_id and messagebox.askyesno("삭제 확인", "정말 삭제하시겠습니까?", parent=self):
            self.manager.delete(item_id)
            self._populate()
            if self.on_refresh:
                self.on_refresh()
