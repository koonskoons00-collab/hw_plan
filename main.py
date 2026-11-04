import calendar
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from models import AssignmentManager
from dialogs import AssignmentDialog, CompletedDialog
from holiday_api import HolidayApiError, fetch_public_holidays


class AssignmentApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("대학생 과제 일정 관리 프로그램")
        self.geometry("960x580")
        self.minsize(860, 500)
        self.manager = AssignmentManager()

        today = datetime.now()
        self.cur_year, self.cur_month = today.year, today.month
        self.selected_date = None

        # 연도별 공휴일 자료를 저장하고, 작업 스레드의 결과를 안전하게 전달한다.
        self.holidays_by_year = {}
        self.holiday_errors = {}
        self.holiday_loading = set()
        self.holiday_queue = queue.Queue()

        self._build_ui()
        self.refresh_all()
        self.after(150, self._poll_holiday_queue)
        self._load_holidays(self.cur_year)

        self.lift()
        self.attributes('-topmost', True)
        self.after_idle(self.attributes, '-topmost', False)
        self.focus_force()

    def _build_ui(self):
        self.banner = tk.Label(self, text="", font=("맑은 고딕", 10, "bold"), pady=6)
        self.banner.pack(fill=tk.X)

        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        # 캘린더 영역
        cal_box = ttk.LabelFrame(paned, text="캘린더", padding=8)
        paned.add(cal_box, weight=1)
        nav = ttk.Frame(cal_box)
        nav.pack(fill=tk.X, pady=(0, 4))
        ttk.Button(nav, text="◀", width=3, command=lambda: self._shift_month(-1)).pack(side=tk.LEFT)
        self.lbl_cal_title = ttk.Label(nav, text="", font=("맑은 고딕", 11, "bold"))
        self.lbl_cal_title.pack(side=tk.LEFT, expand=True)
        ttk.Button(nav, text="▶", width=3, command=lambda: self._shift_month(1)).pack(side=tk.LEFT)
        ttk.Button(nav, text="오늘", width=4, command=self._goto_today).pack(side=tk.LEFT, padx=(3, 0))

        # API 데이터를 다시 요청할 수 있도록 버튼을 추가한다.
        api_nav = ttk.Frame(cal_box)
        api_nav.pack(fill=tk.X, pady=(0, 4))
        ttk.Button(api_nav, text="공휴일 새로고침", command=self._refresh_holidays).pack(side=tk.LEFT)
        self.lbl_holiday_state = ttk.Label(api_nav, text="공휴일 조회 전", wraplength=240)
        self.lbl_holiday_state.pack(side=tk.LEFT, padx=(6, 0))

        days_hdr = ttk.Frame(cal_box)
        days_hdr.pack(fill=tk.X)
        for i, d in enumerate(["일", "월", "화", "수", "목", "금", "토"]):
            fg = "red" if i == 0 else ("blue" if i == 6 else "black")
            tk.Label(days_hdr, text=d, fg=fg, width=4, font=("맑은 고딕", 9, "bold")).pack(side=tk.LEFT, expand=True)

        self.cal_grid = ttk.Frame(cal_box)
        self.cal_grid.pack(fill=tk.BOTH, expand=True, pady=4)

        # 과제 목록 영역
        list_box = ttk.LabelFrame(paned, text="과제 목록", padding=8)
        paned.add(list_box, weight=2)
        top = ttk.Frame(list_box)
        top.pack(fill=tk.X, pady=(0, 4))
        self.lbl_list_title = ttk.Label(top, text="전체 과제", font=("맑은 고딕", 10, "bold"))
        self.lbl_list_title.pack(side=tk.LEFT)
        ttk.Button(top, text="전체 보기", command=self._show_all).pack(side=tk.RIGHT)

        cols = ("subject", "title", "due", "remaining")
        self.tree = ttk.Treeview(list_box, columns=cols, show="headings", selectmode="browse")
        for c, h, w, a in [("subject", "과목명", 110, tk.W), ("title", "과제명", 220, tk.W),
                           ("due", "마감 일시", 120, tk.CENTER), ("remaining", "남은 시간", 150, tk.CENTER)]:
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor=a)
        self.tree.tag_configure("urgent", foreground="#D32F2F", font=("맑은 고딕", 9, "bold"))
        scroll = ttk.Scrollbar(list_box, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.TOP)
        scroll.pack(fill=tk.Y, side=tk.RIGHT, before=self.tree)
        self.tree.bind("<Double-1>", lambda e: self._on_edit())

        btn_bar = ttk.Frame(list_box, padding=(0, 6, 0, 0))
        btn_bar.pack(fill=tk.X)
        actions = [("➕ 과제 추가", self._on_add), ("✏️ 과제 수정", self._on_edit),
                   ("✔️ 완료", self._on_complete), ("🗑️ 삭제", self._on_delete)]
        for text, cmd in actions:
            ttk.Button(btn_bar, text=text, command=cmd).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="📦 완료된 과제", command=self._on_view_completed).pack(side=tk.RIGHT, padx=2)

    def _holiday_name(self, day_str):
        year = int(day_str[:4])
        return self.holidays_by_year.get(year, {}).get(day_str)

    def _update_holiday_state(self):
        if self.cur_year in self.holiday_loading:
            self.lbl_holiday_state.config(text="공휴일 조회 중...")
            return
        if self.cur_year in self.holiday_errors:
            self.lbl_holiday_state.config(text="공휴일 조회 실패 (기본 기능 사용 가능)")
            return
        if self.selected_date and self.selected_date.startswith(f"{self.cur_year}-"):
            name = self._holiday_name(self.selected_date)
            if name:
                self.lbl_holiday_state.config(text=f"선택 날짜 공휴일: {name}")
                return
        if self.cur_year in self.holidays_by_year:
            self.lbl_holiday_state.config(text=f"{self.cur_year}년 공휴일 {len(self.holidays_by_year[self.cur_year])}건")
        else:
            self.lbl_holiday_state.config(text="공휴일 정보 없음")

    def refresh_all(self):
        urgent = self.manager.get_urgent()
        if urgent:
            top = urgent[0]
            self.banner.config(text=f"⚠️ 마감 임박 과제 {len(urgent)}건! [{top.subject}] {top.title} ({top.time_remaining_str()})", bg="#FFCDD2", fg="#B71C1C")
        else:
            self.banner.config(text="✨ 마감 임박(3일 이내) 과제가 없습니다. 편안한 하루 되세요!", bg="#E8F5E9", fg="#1B5E20")

        for w in self.cal_grid.winfo_children():
            w.destroy()
        self.lbl_cal_title.config(text=f"{self.cur_year}년 {self.cur_month:02d}월")
        cal = calendar.Calendar(firstweekday=6)
        counts = self.manager.get_due_count_map()
        today_str = datetime.now().strftime("%Y-%m-%d")
        for r, week in enumerate(cal.monthdatescalendar(self.cur_year, self.cur_month)):
            for c, day_date in enumerate(week):
                d_str = day_date.strftime("%Y-%m-%d")
                in_month = day_date.month == self.cur_month
                cnt = counts.get(d_str, 0)
                holiday = self._holiday_name(d_str) if in_month else None
                text = f"{day_date.day}\n({cnt})" if cnt and in_month else str(day_date.day)
                if holiday:
                    text += "\n휴일"
                if cnt and in_month:
                    bg = "#FFE0B2"
                elif holiday:
                    bg = "#F8BBD0"
                elif d_str == today_str:
                    bg = "#BBDEFB"
                else:
                    bg = "white"
                fg = "red" if holiday else ("black" if in_month else "#BDBDBD")
                btn = tk.Button(self.cal_grid, text=text, bg=bg, fg=fg,
                                relief="solid", bd=1, font=("맑은 고딕", 8, "bold" if d_str == today_str else "normal"),
                                command=lambda s=d_str: self._on_date_click(s))
                btn.grid(row=r, column=c, sticky="nsew", padx=1, pady=1)
                self.cal_grid.grid_columnconfigure(c, weight=1)
            self.cal_grid.grid_rowconfigure(r, weight=1)

        for item in self.tree.get_children():
            self.tree.delete(item)
        items = self.manager.get_active(self.selected_date)
        title_txt = f"{self.selected_date} 과제 ({len(items)}건)" if self.selected_date else f"전체 미완료 과제 ({len(items)}건)"
        self.lbl_list_title.config(text=title_txt)
        for a in items:
            tag = "urgent" if a.is_urgent() else ""
            holiday_mark = " [공휴일]" if self._holiday_name(a.due_date) else ""
            self.tree.insert("", tk.END, iid=str(a.id),
                             values=(a.subject, a.title + holiday_mark, f"{a.due_date} {a.due_time}", a.time_remaining_str()),
                             tags=(tag,) if tag else ())
        self._update_holiday_state()

    def _load_holidays(self, year, force=False):
        if year in self.holiday_loading or (year in self.holidays_by_year and not force):
            return
        self.holiday_loading.add(year)
        self.holiday_errors.pop(year, None)
        self._update_holiday_state()
        threading.Thread(target=self._fetch_holidays_worker, args=(year,), daemon=True).start()

    def _fetch_holidays_worker(self, year):
        try:
            result = fetch_public_holidays(year)
            self.holiday_queue.put((year, result, None))
        except (HolidayApiError, ValueError) as error:
            self.holiday_queue.put((year, None, str(error)))

    def _poll_holiday_queue(self):
        try:
            while True:
                year, holidays, error = self.holiday_queue.get_nowait()
                self.holiday_loading.discard(year)
                if error:
                    self.holiday_errors[year] = error
                else:
                    self.holidays_by_year[year] = holidays
                    self.holiday_errors.pop(year, None)
                self.refresh_all()
        except queue.Empty:
            pass
        self.after(150, self._poll_holiday_queue)

    def _refresh_holidays(self):
        self._load_holidays(self.cur_year, force=True)

    def _selected_item(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("안내", "과제를 먼저 선택해주세요.", parent=self)
            return None
        return next((a for a in self.manager.assignments if a.id == int(sel[0])), None)

    def _on_date_click(self, date_str):
        self.selected_date = date_str
        self.refresh_all()

    def _show_all(self):
        self.selected_date = None
        self.refresh_all()

    def _shift_month(self, delta):
        m = self.cur_month + delta
        if m < 1:
            self.cur_month, self.cur_year = 12, self.cur_year - 1
        elif m > 12:
            self.cur_month, self.cur_year = 1, self.cur_year + 1
        else:
            self.cur_month = m
        self.refresh_all()
        self._load_holidays(self.cur_year)

    def _goto_today(self):
        t = datetime.now()
        self.cur_year, self.cur_month = t.year, t.month
        self.selected_date = t.strftime("%Y-%m-%d")
        self.refresh_all()
        self._load_holidays(self.cur_year)

    def _on_add(self):
        AssignmentDialog(self, self.manager, default_date=self.selected_date, on_success=self.refresh_all)

    def _on_edit(self):
        item = self._selected_item()
        if item:
            AssignmentDialog(self, self.manager, item=item, on_success=self.refresh_all)

    def _on_complete(self):
        item = self._selected_item()
        if item:
            self.manager.toggle_complete(item.id)
            messagebox.showinfo("완료", f"'{item.title}' 과제가 완료 처리되었습니다!\n[완료된 과제] 보관함에서 확인 가능합니다.", parent=self)
            self.refresh_all()

    def _on_delete(self):
        item = self._selected_item()
        if item and messagebox.askyesno("삭제 확인", f"'{item.title}' 과제를 삭제하시겠습니까?", parent=self):
            self.manager.delete(item.id)
            self.refresh_all()

    def _on_view_completed(self):
        CompletedDialog(self, self.manager, on_refresh=self.refresh_all)


if __name__ == "__main__":
    app = AssignmentApp()
    app.mainloop()
