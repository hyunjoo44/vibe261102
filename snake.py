"""뱀 게임 (tkinter 사용 - 별도 설치 불필요)

조작법:
  방향키 / WASD : 이동
  P             : 일시정지
  R             : 재시작 (게임 오버 후)
  Esc           : 종료
"""
import random
import tkinter as tk

CELL = 20          # 칸 크기(px)
COLS = 30          # 가로 칸 수
ROWS = 24          # 세로 칸 수
START_SPEED = 120  # 시작 속도(ms, 작을수록 빠름)
MIN_SPEED = 50     # 최고 속도

DIRECTIONS = {
    "Up": (0, -1), "w": (0, -1),
    "Down": (0, 1), "s": (0, 1),
    "Left": (-1, 0), "a": (-1, 0),
    "Right": (1, 0), "d": (1, 0),
}


class SnakeGame:
    def __init__(self, root):
        self.root = root
        root.title("Snake")
        root.resizable(False, False)

        self.canvas = tk.Canvas(root, width=COLS * CELL, height=ROWS * CELL,
                                bg="#1e1e1e", highlightthickness=0)
        self.canvas.pack()
        self.status = tk.Label(root, font=("Consolas", 12), anchor="w",
                               bg="#2d2d2d", fg="white")
        self.status.pack(fill="x")

        self.high_score = 0
        self.after_id = None
        root.bind("<Key>", self.on_key)
        self.reset()

    def reset(self):
        if self.after_id:
            self.root.after_cancel(self.after_id)
        cx, cy = COLS // 2, ROWS // 2
        self.snake = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]
        self.direction = (1, 0)
        self.next_direction = (1, 0)
        self.score = 0
        self.speed = START_SPEED
        self.paused = False
        self.game_over = False
        self.food = self.place_food()
        self.draw()
        self.tick()

    def place_food(self):
        free = [(x, y) for x in range(COLS) for y in range(ROWS)
                if (x, y) not in self.snake]
        return random.choice(free) if free else None

    def on_key(self, event):
        key = event.keysym if event.keysym in DIRECTIONS else event.keysym.lower()
        if key in DIRECTIONS:
            dx, dy = DIRECTIONS[key]
            # 반대 방향으로는 바로 꺾을 수 없음
            if (dx, dy) != (-self.direction[0], -self.direction[1]):
                self.next_direction = (dx, dy)
        elif key == "p" and not self.game_over:
            self.paused = not self.paused
            self.draw()
        elif key == "r" and self.game_over:
            self.reset()
        elif key == "escape":
            self.root.destroy()

    def tick(self):
        if not self.paused and not self.game_over:
            self.step()
            self.draw()
        self.after_id = self.root.after(self.speed, self.tick)

    def step(self):
        self.direction = self.next_direction
        hx, hy = self.snake[0]
        new_head = (hx + self.direction[0], hy + self.direction[1])

        will_eat = new_head == self.food
        body = self.snake if will_eat else self.snake[:-1]  # 꼬리는 이동하므로 제외

        if (not (0 <= new_head[0] < COLS and 0 <= new_head[1] < ROWS)
                or new_head in body):
            self.game_over = True
            self.high_score = max(self.high_score, self.score)
            return

        self.snake.insert(0, new_head)
        if will_eat:
            self.score += 10
            self.speed = max(MIN_SPEED, self.speed - 3)
            self.food = self.place_food()
            if self.food is None:  # 화면을 꽉 채우면 승리
                self.game_over = True
                self.high_score = max(self.high_score, self.score)
        else:
            self.snake.pop()

    def draw(self):
        c = self.canvas
        c.delete("all")

        if self.food:
            fx, fy = self.food
            c.create_oval(fx * CELL + 3, fy * CELL + 3,
                          (fx + 1) * CELL - 3, (fy + 1) * CELL - 3,
                          fill="#e74c3c", outline="")

        for i, (x, y) in enumerate(self.snake):
            color = "#2ecc71" if i == 0 else "#27ae60"
            c.create_rectangle(x * CELL + 1, y * CELL + 1,
                               (x + 1) * CELL - 1, (y + 1) * CELL - 1,
                               fill=color, outline="")

        w, h = COLS * CELL, ROWS * CELL
        if self.game_over:
            msg = "YOU WIN!" if self.food is None else "GAME OVER"
            c.create_text(w / 2, h / 2 - 20, text=msg,
                          fill="white", font=("Consolas", 32, "bold"))
            c.create_text(w / 2, h / 2 + 20, text="R: 재시작   Esc: 종료",
                          fill="#cccccc", font=("Consolas", 14))
        elif self.paused:
            c.create_text(w / 2, h / 2, text="PAUSED",
                          fill="white", font=("Consolas", 32, "bold"))

        self.status.config(
            text=f"  점수: {self.score}    최고 점수: {self.high_score}    길이: {len(self.snake)}")


if __name__ == "__main__":
    root = tk.Tk()
    SnakeGame(root)
    root.mainloop()
