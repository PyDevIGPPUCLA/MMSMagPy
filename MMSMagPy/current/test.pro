pro run
  np = 2
  magData = dblarr(4, 4, np) ; [4 sc, b{x,y,z,t}, index]
  posData = dblarr(4, 4, np)
; for i = 0, np - 1 do begin
;   magData[*,*, i] = i
;   posData[*,*, i] = i
; end
; for i = 0, 3 do begin
;   magData[i,*, *] += i * 10
;   posData[i,*, *] += i * 10
; end
  dr = !pi / 16
  for i = 0, 3 do begin    ; space craft
    c = i * 3
    d = i * 2
    for j = 0, 3 do begin  ; bx,by,bz,bt
      index = i * 4 + j
      for k = 0, np - 1 do begin   ; time
        magData[i,j,k] = 100 * i + 10 * j + k 
        posData[i,j,k] = c * i + d * j + k
      end
      posData[i,j,0] = 20 * sin(index * dr)
      posData[i,j,1] = 10 * sin(index * dr)
;     print, index, index * dr, sin(index * dr)
    end
  end
; print,magData[0, *, *]
; print,magData[*, *, 1]
;print,"bof"
;print,posData[0,*,0]
;print,"bof"
;print,posData[1,*,0]
;print,"bof"
;print,posData[2,*,0]
;print,"bof"
;print,posData[3,*,0]
  x = current(magData, posData, qlfactor=qlfactor, curlB=curlB)
end
