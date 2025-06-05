def on_button_pressed_a():
    music.play(music.tone_playable(523, music.beat(BeatFraction.QUARTER)),
        music.PlaybackMode.UNTIL_DONE)
    music.play(music.tone_playable(392, music.beat(BeatFraction.WHOLE)),
        music.PlaybackMode.UNTIL_DONE)
    serial.write_line("A")
    basic.show_string("A")
    basic.pause(200)
    basic.clear_screen()
    basic.show_icon(IconNames.HAPPY)
input.on_button_pressed(Button.A, on_button_pressed_a)

def on_button_pressed_ab():
    music.play(music.tone_playable(349, music.beat(BeatFraction.WHOLE)),
        music.PlaybackMode.UNTIL_DONE)
    serial.write_line("C")
    basic.show_string("C")
    basic.pause(200)
    basic.clear_screen()
    basic.show_icon(IconNames.HAPPY)
input.on_button_pressed(Button.AB, on_button_pressed_ab)

def on_button_pressed_b():
    music.play(music.tone_playable(392, music.beat(BeatFraction.WHOLE)),
        music.PlaybackMode.UNTIL_DONE)
    music.play(music.tone_playable(523, music.beat(BeatFraction.QUARTER)),
        music.PlaybackMode.UNTIL_DONE)
    serial.write_line("B")
    basic.show_string("B")
    basic.pause(200)
    basic.clear_screen()
    basic.show_icon(IconNames.HAPPY)
input.on_button_pressed(Button.B, on_button_pressed_b)

sonar2 = 0
current_light_value = 0
basic.show_icon(IconNames.HAPPY)

def on_forever():
    global current_light_value
    current_light_value = pins.analog_read_pin(AnalogPin.P0)
    serial.write_line("" + str(current_light_value))
    basic.pause(10000)
basic.forever(on_forever)

def on_forever2():
    global sonar2
    sonar2 = sonar.ping(DigitalPin.P9, DigitalPin.P8, PingUnit.CENTIMETERS)
    if 10 < sonar2 and sonar2 < 40:
        music.play(music.tone_playable(494, music.beat(BeatFraction.HALF)),
            music.PlaybackMode.UNTIL_DONE)
        basic.pause(100)
        music.play(music.tone_playable(494, music.beat(BeatFraction.QUARTER)),
            music.PlaybackMode.UNTIL_DONE)
        basic.pause(1000)
    else:
        pass
basic.forever(on_forever2)
