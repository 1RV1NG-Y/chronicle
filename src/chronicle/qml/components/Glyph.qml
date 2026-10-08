import QtQuick

Canvas {
    id: root
    property string name: "day"
    property color ink: "white"
    implicitWidth: 18
    implicitHeight: 18
    onNameChanged: requestPaint()
    onInkChanged: requestPaint()
    onPaint: {
        var c = getContext("2d")
        c.reset()
        c.scale(width / 24, height / 24)
        c.strokeStyle = ink
        c.lineWidth = 1.6
        c.lineCap = "round"
        c.lineJoin = "round"
        c.beginPath()
        if (name === "day") {
            c.rect(4, 5, 16, 16)
            c.moveTo(4, 10); c.lineTo(20, 10)
            c.moveTo(8, 3); c.lineTo(8, 7)
            c.moveTo(16, 3); c.lineTo(16, 7)
            c.moveTo(8, 14); c.lineTo(11, 14)
            c.moveTo(8, 17); c.lineTo(15, 17)
        } else if (name === "list") {
            for (var y = 6; y <= 18; y += 6) {
                c.moveTo(9, y); c.lineTo(20, y)
                c.moveTo(4, y); c.lineTo(4.5, y)
            }
        } else if (name === "settings") {
            for (var x = 6; x <= 18; x += 6) {
                var cy = x === 12 ? 15 : 9
                c.moveTo(x, 4); c.lineTo(x, cy - 2)
                c.moveTo(x, cy + 2); c.lineTo(x, 20)
                c.moveTo(x + 2, cy); c.arc(x, cy, 2, 0, Math.PI * 2)
            }
        } else if (name === "left" || name === "right") {
            var sign = name === "left" ? 1 : -1
            c.moveTo(12 + 3 * sign, 6); c.lineTo(12 - 3 * sign, 12); c.lineTo(12 + 3 * sign, 18)
        } else if (name === "close") {
            c.moveTo(6, 6); c.lineTo(18, 18)
            c.moveTo(18, 6); c.lineTo(6, 18)
        } else if (name === "search") {
            c.arc(10, 10, 6, 0, Math.PI * 2)
            c.moveTo(15, 15); c.lineTo(20, 20)
        } else {
            c.arc(12, 12, 8, 0, Math.PI * 2)
            c.moveTo(12, 7); c.lineTo(12, 12); c.lineTo(16, 14)
        }
        c.stroke()
    }
}
