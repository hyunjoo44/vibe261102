import tkinter as tk


class BlockBreaker:
    WIDTH = 800
    HEIGHT = 600
    BALL_RADIUS = 9
    PADDLE_WIDTH = 110
    PADDLE_HEIGHT = 14
    PADDLE_SPEED = 8
    BRICK_ROWS = 5
    BRICK_COLUMNS = 10
    BRICK_WIDTH = 68
    BRICK_HEIGHT = 22
    BRICK_GAP = 7

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("블럭깨기")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(
            root,
            width=self.WIDTH,
            height=self.HEIGHT,
            bg="#101827",
            highlightthickness=0,
        )
        self.canvas.pack()

        self.keys: set[str] = set()
        self.paused = False
        self.game_over = False
        self.score = 0
        self.lives = 3
        self.paddle_x = self.WIDTH / 2
        self.ball_x = self.WIDTH / 2
        self.ball_y = self.HEIGHT - 90
        self.ball_dx = 4
        self.ball_dy = -4
        self.bricks: dict[int, tuple[int, int]] = {}
        self.status_text = 0
        self.score_text = 0
        self.lives_text = 0
        self.paddle = 0
        self.ball = 0

        self.root.bind("<KeyPress-Left>", lambda _event: self.keys.add("Left"))
        self.root.bind("<KeyRelease-Left>", lambda _event: self.keys.discard("Left"))
        self.root.bind("<KeyPress-Right>", lambda _event: self.keys.add("Right"))
        self.root.bind("<KeyRelease-Right>", lambda _event: self.keys.discard("Right"))
        self.root.bind("<Motion>", self.move_paddle_with_mouse)
        self.root.bind("<space>", self.toggle_pause)
        self.root.bind("<r>", self.restart)
        self.root.bind("<R>", self.restart)

        self.draw_scene()
        self.create_bricks()
        self.draw_hud()
        self.update_game()

    def draw_scene(self) -> None:
        self.canvas.create_text(
            self.WIDTH / 2,
            20,
            text="BLOCK BREAKER",
            fill="#cbd5e1",
            font=("Arial", 12, "bold"),
        )
        self.paddle = self.canvas.create_rectangle(
            0, 0, 0, 0, fill="#38bdf8", outline=""
        )
        self.ball = self.canvas.create_oval(
            0, 0, 0, 0, fill="#f8fafc", outline=""
        )
        self.status_text = self.canvas.create_text(
            self.WIDTH / 2,
            self.HEIGHT / 2,
            text="",
            fill="#f8fafc",
            font=("Arial", 24, "bold"),
        )
        self.position_paddle()
        self.position_ball()

    def create_bricks(self) -> None:
        colors = ["#fb7185", "#fb923c", "#facc15", "#4ade80", "#60a5fa"]
        total_width = (
            self.BRICK_COLUMNS * self.BRICK_WIDTH
            + (self.BRICK_COLUMNS - 1) * self.BRICK_GAP
        )
        left_margin = (self.WIDTH - total_width) / 2

        for row in range(self.BRICK_ROWS):
            for column in range(self.BRICK_COLUMNS):
                x1 = left_margin + column * (self.BRICK_WIDTH + self.BRICK_GAP)
                y1 = 55 + row * (self.BRICK_HEIGHT + self.BRICK_GAP)
                brick = self.canvas.create_rectangle(
                    x1,
                    y1,
                    x1 + self.BRICK_WIDTH,
                    y1 + self.BRICK_HEIGHT,
                    fill=colors[row],
                    outline="#101827",
                    width=2,
                )
                self.bricks[brick] = (row, column)

    def draw_hud(self) -> None:
        self.score_text = self.canvas.create_text(
            18, 20, anchor="w", text="", fill="#f8fafc", font=("Arial", 12)
        )
        self.lives_text = self.canvas.create_text(
            self.WIDTH - 18,
            20,
            anchor="e",
            text="",
            fill="#f8fafc",
            font=("Arial", 12),
        )
        self.update_hud()

    def update_hud(self) -> None:
        self.canvas.itemconfigure(self.score_text, text=f"점수: {self.score}")
        self.canvas.itemconfigure(self.lives_text, text=f"목숨: {self.lives}")

    def position_paddle(self) -> None:
        half_width = self.PADDLE_WIDTH / 2
        self.canvas.coords(
            self.paddle,
            self.paddle_x - half_width,
            self.HEIGHT - 42,
            self.paddle_x + half_width,
            self.HEIGHT - 42 + self.PADDLE_HEIGHT,
        )

    def position_ball(self) -> None:
        radius = self.BALL_RADIUS
        self.canvas.coords(
            self.ball,
            self.ball_x - radius,
            self.ball_y - radius,
            self.ball_x + radius,
            self.ball_y + radius,
        )

    def move_paddle_with_mouse(self, event: tk.Event) -> None:
        half_width = self.PADDLE_WIDTH / 2
        self.paddle_x = max(half_width, min(self.WIDTH - half_width, event.x))
        self.position_paddle()

    def toggle_pause(self, _event: tk.Event | None = None) -> None:
        if self.game_over:
            return
        self.paused = not self.paused
        self.canvas.itemconfigure(
            self.status_text, text="일시정지" if self.paused else ""
        )

    def restart(self, _event: tk.Event | None = None) -> None:
        self.canvas.delete("all")
        self.keys.clear()
        self.paused = False
        self.game_over = False
        self.score = 0
        self.lives = 3
        self.paddle_x = self.WIDTH / 2
        self.ball_x = self.WIDTH / 2
        self.ball_y = self.HEIGHT - 90
        self.ball_dx = 4
        self.ball_dy = -4
        self.bricks.clear()
        self.draw_scene()
        self.create_bricks()
        self.draw_hud()

    def end_game(self, message: str) -> None:
        self.game_over = True
        self.canvas.itemconfigure(
            self.status_text,
            text=f"{message}\nR 키를 눌러 다시 시작",
        )

    def update_game(self) -> None:
        if not self.paused and not self.game_over:
            self.move_paddle()
            self.move_ball()

        self.root.after(16, self.update_game)

    def move_paddle(self) -> None:
        if "Left" in self.keys:
            self.paddle_x -= self.PADDLE_SPEED
        if "Right" in self.keys:
            self.paddle_x += self.PADDLE_SPEED
        half_width = self.PADDLE_WIDTH / 2
        self.paddle_x = max(half_width, min(self.WIDTH - half_width, self.paddle_x))
        self.position_paddle()

    def move_ball(self) -> None:
        self.ball_x += self.ball_dx
        self.ball_y += self.ball_dy
        radius = self.BALL_RADIUS

        if self.ball_x - radius <= 0 or self.ball_x + radius >= self.WIDTH:
            self.ball_dx *= -1
        if self.ball_y - radius <= 0:
            self.ball_dy = abs(self.ball_dy)

        paddle_left = self.paddle_x - self.PADDLE_WIDTH / 2
        paddle_right = self.paddle_x + self.PADDLE_WIDTH / 2
        paddle_top = self.HEIGHT - 42
        if (
            self.ball_dy > 0
            and paddle_left - radius <= self.ball_x <= paddle_right + radius
            and paddle_top - radius <= self.ball_y <= paddle_top + self.PADDLE_HEIGHT
        ):
            hit_position = (self.ball_x - self.paddle_x) / (self.PADDLE_WIDTH / 2)
            self.ball_dx = hit_position * 5
            self.ball_dy = -max(3, (self.ball_dx**2 + self.ball_dy**2) ** 0.5)

        self.check_brick_collision()
        if self.ball_y - radius > self.HEIGHT:
            self.lives -= 1
            self.update_hud()
            if self.lives <= 0:
                self.end_game("게임 오버")
            else:
                self.reset_ball()

        self.position_ball()

    def check_brick_collision(self) -> None:
        radius = self.BALL_RADIUS
        overlapping = self.canvas.find_overlapping(
            self.ball_x - radius,
            self.ball_y - radius,
            self.ball_x + radius,
            self.ball_y + radius,
        )
        for item in overlapping:
            if item not in self.bricks:
                continue
            x1, y1, x2, y2 = self.canvas.coords(item)
            if self.ball_x - radius < x1 or self.ball_x + radius > x2:
                self.ball_dx *= -1
            else:
                self.ball_dy *= -1
            self.canvas.delete(item)
            del self.bricks[item]
            self.score += 10
            self.update_hud()
            if not self.bricks:
                self.end_game("승리!")
            return

    def reset_ball(self) -> None:
        self.ball_x = self.paddle_x
        self.ball_y = self.HEIGHT - 90
        self.ball_dx = 4
        self.ball_dy = -4
        self.position_ball()


def main() -> None:
    root = tk.Tk()
    BlockBreaker(root)
    root.mainloop()


if __name__ == "__main__":
    main()
