"""Значок: два облачка разговора — переднее белое, заднее полупрозрачное.

Рисуем один слой на прозрачном фоне: подложку, тень и блик macOS накладывает
сама, по-своему для светлой и тёмной темы (Icon Composer).
"""
import sys

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPainterPath, QLinearGradient

S = 1024


def bubble(x, y, w, h, tail_left):
    """Облачко: скруглённый прямоугольник и хвостик снизу."""
    path = QPainterPath()
    path.addRoundedRect(QRectF(x, y, w, h), h * 0.42, h * 0.42)
    tail = QPainterPath()
    base = y + h - 6
    if tail_left:
        bx = x + w * 0.26
        tail.moveTo(bx - 40, base)
        tail.lineTo(bx - 95, y + h + 85)
        tail.lineTo(bx + 75, base)
    else:
        bx = x + w * 0.74
        tail.moveTo(bx + 40, base)
        tail.lineTo(bx + 95, y + h + 85)
        tail.lineTo(bx - 75, base)
    tail.closeSubpath()
    return path.united(tail)


def draw(path, layer=False):
    QGuiApplication.instance() or QGuiApplication([])
    img = QImage(S, S, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    if not layer:
        g = QLinearGradient(0, 0, 0, S)
        g.setColorAt(0, QColor("#97b0ff"))
        g.setColorAt(1, QColor("#6a86f0"))
        p.fillRect(QRectF(0, 0, S, S), g)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 255, 255, 120))
    p.drawPath(bubble(330, 230, 470, 300, tail_left=False))
    p.setBrush(QColor("#ffffff"))
    p.drawPath(bubble(210, 430, 500, 320, tail_left=True))
    p.end()
    img.save(path)


if __name__ == "__main__":
    draw(sys.argv[1] if len(sys.argv) > 1 else "icon/AppIcon-1024.png",
         len(sys.argv) > 2 and sys.argv[2] == "layer")
