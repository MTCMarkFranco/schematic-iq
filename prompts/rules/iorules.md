RULE INPUT_1:
  Terminal inputs occur on the short side of the rectangle

RULE INPUT_2:
  Input side is LEFT or TOP depending on terminal orientation

RULE INPUT_3:
  A terminal input may have:
    0 connections
    1 connection
    2 connections (max)

RULE INPUT_4:
  Connection geometry meaning:
    0 lines → no connection
    1 perpendicular line → single connection
    2 lines:
      - one perpendicular
      - one angled
      → two connections
