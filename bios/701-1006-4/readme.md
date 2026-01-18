### BIOS 701.1006.4
 
## Warning: DO NOT USE THIS VERSION!

It has a bug that prevents internal keyboard from working correctly.
Please use [701-1006-1](https://github.com/rustyJ4ck/EeePC701/tree/main/bios/701-1006-1) bios for now, while we investigate the issue with keyboard.

Fix if you already flashed this revision: flash back 1006-1.

Временный фикс:
* Прошить версию 1006.1
* После прошивки выключить, отключить адаптер питания и батарею, после этого нажать у удерживать 30 секунд кнопку питания
* Далее, возвращаем питание, включаем компьютер, F1 - использовать настройки биос по-умолчанию
* Сразу прошиваем версию 1006.4
* Перезагрузка - клавиатура должна работать 
