from __future__ import annotations

from typing import Tuple, Any, Optional
from pathlib import Path
import tempfile

from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np


def extract_frame(video: Any, time_seconds: float = 10.0) -> np.ndarray:
    """Извлечь кадр из видео в указанное время как numpy array."""
    frame = video.get_frame(time_seconds)
    return frame


def show_frame_with_grid(frame: np.ndarray, title: str = "Видеокадр") -> None:
    """Показать кадр с координатной сеткой для удобства выбора области кропа."""
    height, width = frame.shape[:2]
    
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    ax.imshow(frame)
    ax.set_title(f"{title} ({width}x{height})")
    
    # Добавим сетку каждые 100 пикселей для удобства
    for x in range(0, width, 100):
        ax.axvline(x, color='white', alpha=0.3, linewidth=0.5)
        if x % 200 == 0:  # подписи каждые 200px
            ax.text(x, 20, str(x), color='white', fontsize=8, ha='center')
    
    for y in range(0, height, 100):
        ax.axhline(y, color='white', alpha=0.3, linewidth=0.5)
        if y % 200 == 0:
            ax.text(20, y, str(y), color='white', fontsize=8, va='center')
    
    plt.tight_layout()
    plt.show()


def interactive_crop_selector(video: Any, time_seconds: float = 10.0) -> Tuple[int, int, int, int]:
    """Интерактивный выбор области кропа с фиксированным соотношением 9:16."""
    frame = extract_frame(video, time_seconds)
    height, width = frame.shape[:2]
    
    print(f"Кадр: {width}x{height}. Настройте область кропа 9:16.")
    print("Управление:")
    print("• Клик мыши - переместить центр области")
    print("• Колесо мыши - изменить размер")
    print("• Клавиши +/- - изменить размер")
    print("• Закройте окно когда готово")
    
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    ax.imshow(frame)
    ax.set_title(f"Настройка кропа 9:16 ({width}x{height})")
    
    # Начальные параметры кропа
    default_crop = get_default_crop_for_vertical(width, height)
    current_width = default_crop[2] - default_crop[0]
    current_height = default_crop[3] - default_crop[1]
    center_x = (default_crop[0] + default_crop[2]) // 2
    center_y = (default_crop[1] + default_crop[3]) // 2
    
    # Переменная для хранения результата
    crop_coords = list(default_crop)
    
    # Прямоугольник для показа текущей области
    rect = patches.Rectangle((crop_coords[0], crop_coords[1]), 
                           current_width, current_height,
                           linewidth=2, edgecolor='red', facecolor='none', alpha=0.7)
    ax.add_patch(rect)
    
    def update_crop(new_center_x=None, new_center_y=None, scale_factor=1.0):
        """Обновить область кропа с новым центром и/или размером."""
        nonlocal center_x, center_y, current_width, current_height
        
        if new_center_x is not None:
            center_x = new_center_x
        if new_center_y is not None:
            center_y = new_center_y
            
        # Изменяем размер с сохранением пропорций 9:16
        target_ratio = 9 / 16
        
        if scale_factor != 1.0:
            new_width = int(current_width * scale_factor)
            new_height = int(new_width / target_ratio)
            
            # Проверяем, помещается ли в кадр
            if new_width <= width and new_height <= height and new_width >= 50:
                current_width = new_width
                current_height = new_height
        
        # Центрируем относительно указанной точки, но не выходим за границы
        x1 = max(0, min(center_x - current_width // 2, width - current_width))
        y1 = max(0, min(center_y - current_height // 2, height - current_height))
        x2 = x1 + current_width
        y2 = y1 + current_height
        
        # Обновляем координаты
        crop_coords[:] = [x1, y1, x2, y2]
        
        # Обновляем прямоугольник
        rect.set_xy((x1, y1))
        rect.set_width(current_width)
        rect.set_height(current_height)
        
        print(f"Кроп: x1={x1}, y1={y1}, x2={x2}, y2={y2}")
        print(f"Размер: {current_width}x{current_height} (соотношение {current_width/current_height:.3f})")
        
        fig.canvas.draw()
    
    def onclick(event):
        """Callback для клика мыши - перемещаем центр кропа."""
        if event.inaxes != ax or event.xdata is None or event.ydata is None:
            return
        update_crop(new_center_x=int(event.xdata), new_center_y=int(event.ydata))
    
    def onscroll(event):
        """Callback для колеса мыши - изменяем размер."""
        if event.inaxes != ax:
            return
        
        # Масштабируем на 10% за шаг
        scale_factor = 1.1 if event.step > 0 else 1/1.1
        update_crop(scale_factor=scale_factor)
    
    def onkey(event):
        """Callback для клавиш - изменяем размер."""
        if event.key == '+' or event.key == '=':
            update_crop(scale_factor=1.1)
        elif event.key == '-':
            update_crop(scale_factor=1/1.1)
    
    # Подключаем обработчики событий
    fig.canvas.mpl_connect('button_press_event', onclick)
    fig.canvas.mpl_connect('scroll_event', onscroll)
    fig.canvas.mpl_connect('key_press_event', onkey)
    
    # Показываем начальное состояние
    update_crop()
    
    plt.tight_layout()
    plt.show()
    
    return (crop_coords[0], crop_coords[1], crop_coords[2], crop_coords[3])


def configure_crop_interactive(video: Any, time_seconds: float = 10.0) -> Tuple[int, int, int, int]:
    """Интерактивная настройка кропа с фиксированным соотношением 9:16.
    
    Returns:
        Tuple (x1, y1, x2, y2) - координаты для кропа
    """
    frame = extract_frame(video, time_seconds)
    height, width = frame.shape[:2]
    
    print(f"=== Настройка кропа видео (соотношение 9:16) ===")
    print(f"Размер кадра: {width} x {height}")
    print(f"Время кадра: {time_seconds}с")
    print()
    
    try:
        coords = interactive_crop_selector(video, time_seconds)
        print(f"\nВыбранные координаты: {coords}")
        x1, y1, x2, y2 = coords
        print(f"Размер кропа: {x2-x1} x {y2-y1}")
        print(f"Соотношение сторон: {(x2-x1)/(y2-y1):.3f} (целевое: 0.562)")
        return coords
        
    except Exception as e:
        print(f"Ошибка визуального выбора: {e}")
        print("Используется автоматический кроп по центру.")
        return get_default_crop_for_vertical(width, height)


def get_default_crop_for_vertical(width: int, height: int) -> Tuple[int, int, int, int]:
    """Получить кроп по умолчанию для вертикального видео (соотношение 9:16)."""
    # Вычисляем центральную область 9:16
    target_ratio = 9 / 16
    current_ratio = width / height
    
    if current_ratio > target_ratio:
        # Видео шире, чем нужно - обрезаем по ширине
        new_width = int(height * target_ratio)
        x1 = (width - new_width) // 2
        x2 = x1 + new_width
        y1, y2 = 0, height
    else:
        # Видео уже или равно нужному соотношению - обрезаем по высоте
        new_height = int(width / target_ratio)
        y1 = (height - new_height) // 2
        y2 = y1 + new_height
        x1, x2 = 0, width
        
    return (x1, y1, x2, y2)