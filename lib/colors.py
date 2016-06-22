# Constants
Background = 'FF111111'
BackgroundDark = 'FF0A0A0A'

#  OverlayVeryDark = GetAlpha(FF000000, 90),
#  OverlayDark = GetAlpha(FF000000, 70),
#  OverlayMed = GetAlpha(FF000000, 50),
#  OverlayLht = GetAlpha(FF000000, 35),

Border = 'FF1F1F1F'
Empty = 'FF1F1F1F'
Card = 'FF1F1F1F'
Button = 'FF1F1F1F'
ButtonDark = 'FF171717'
ButtonLht = 'FF555555'
ButtonMed = 'FF2D2D2D'
Indicator = 'FF999999'
Text = 'FFFFFFFF'
Subtitle = 'FF999999'

# These are dependent on the regions background color
#  TextLht = GetAlpha(FFFFFFFF, 90),
#  TextMed = GetAlpha(FFFFFFFF, 75),
#  TextDim = GetAlpha(FFFFFFFF, 50),
#  TextDis = GetAlpha(FFFFFFFF, 30),
#  TextDimDis = GetAlpha(FFFFFFFF, 10),

Transparent = '00000000'
Black = 'FF000000'
Blue = 'FF0033CC'
Red = 'FFC23529'
RedAlt = 'FFD9534F'
Green = 'FF5CB85C'
Orange = 'FFCC7B19'
OrangeLight = 'FFF9BE03'

# Component specific
#  SettingsBg = 'FF2C2C2C'
#  ScrollbarBg = GetAlpha(FFFFFFFF, 10),
#  ScrollbarFgFocus = GetAlpha('Orange' 70),
#  ScrollbarFg = GetAlpha(FFFFFFFF, 25),
#  IndicatorBorder = 'FF000000'
#  Separator = 'FF000000'
#  Modal = GetAlpha(FF000000, 85),
#  Focus = Orange,
#  FocusToggle = OrangeLight,

#  ListFocusBg = GetAlpha(FF000000, 40),
#  TrackActionsBg = GetAlpha(FF000000, 30),
#  ListBg = GetAlpha(FFFFFFFF, 10),
#  ListBgNoBlur = GetAlpha(FF666666, 40),
#  ListImageBorder = 'FF595959'

SearchBg = 'FF2D2D2D'
SearchButton = 'FF282828'
SearchButtonDark = 'FF1F1F1F'
SearchButtonLight = 'FF555555'

InputBg = 'FF000000'
InputButton = 'FF282828'
InputButtonDark = 'FF1F1F1F'
InputButtonLight = 'FF555555'


class _noAlpha:
    def __getattr__(self, name):
        return globals()[name][2:]

noAlpha = _noAlpha()


# def getAlpha(color, percent):
#     if isinstance(color, basestring):
#         color = COLORS[color]

#     if isinstance(color, int):
#         util.ERROR_LOG(str(color) + " is not found in object")

#     return color and int((percent / 100 * 255) - 256)
