FUNCTION cal_curlometer1, magdata, posdata, qlfactor = qlfactor, curlB = curlB

; --- This program will calculate the current density using the curlometer techinique 

sate_no = indgen(4)
miu3 = 10.0^(0-4.0) * 4.0 * !pi

IF N_ELEMENTS(sate_no) LT 4 THEN stop
np = N_ELEMENTS(magdata[sate_no[0], 0, *])
current = dblarr(4, np) ; --- fifth of 1st dim is ql factor
tcurrent = current
normn   = dblarr(3, np)
norml   = dblarr(np)

; --- set referrence satellite to be s

normdirect = dblarr(3, 3, np)
normj      = dblarr(3, np)
j          = dblarr(3, np)

FOR iside = 0, 2 DO BEGIN
  sten0 = 0 ; --- get the satellite number on this side
  sten1 = sate_no[(iside+1)   MOD 4]
  sten2 = sate_no[(iside+2)   MOD 4]
  IF sten2 EQ 0 THEN sten2 = 1
  magd0 = magdata[sten0, *, *]
  magd1 = magdata[sten1, *, *]
  magd2 = magdata[sten2, *, *]
  delmagd10 = magd1 - magd0
  delmagd20 = magd2 - magd0
  
  posd0 = posdata[sten0, *, *]
  posd1 = posdata[sten1, *, *]
  posd2 = posdata[sten2, *, *] ;;; the definative position data
  r10   = posd1 - posd0;; 
  r20   = posd2 - posd0
  
  ; --- calculate the normal direction
  FOR inp = 0, np - 1 DO BEGIN
    normn[*, inp] = crossp(r10[0:2, inp], r20[0:2, inp])
    norml[inp]    = norm(normn[*, inp])
    normn[*, inp] = normn[*, inp]/norm(normn[*, inp])
  ENDFOR ; --- for inp
  ; --- calculate the current density along normal direction
  tcurrent = ( total(delmagd10[0:2, *] * r20[0:2, *], 1) - total(delmagd20[0:2, *] * r10[0:2, *], 1) )  / (norml * miu3)
  
  ; --- record normal direction and normal current strength
  normdirect[iside, *, *] = normn
  normj[iside, *]         = tcurrent
  
ENDFOR

; ---- solve the functions for the current density
FOR inp = 0, np - 1 DO BEGIN
  normmat = transpose(reform(normdirect[*, *, inp], 3, 3))
  invmat  = invert(normmat)
  current[0:2, inp] = reform(normj[*, inp], 3) # invmat
ENDFOR

; ---- calculate the Volume, surface and formation factor
volm = dblarr(np) ; --- volume
surf = dblarr(np) ; --- total surface area
leng = dblarr(np) ; --- total length
pos0 = posdata[ 0, *, *]
pos1 = posdata[ 1, *, *]
pos2 = posdata[ 2, *, *]
pos3 = posdata[ 3, *, *]

FOR inp = 0, np-1 DO BEGIN
  refpos = pos0[0:2, inp]
  volm[inp] = abs((pos1[0:2, inp] - refpos) ## transpose( crossp(pos2[0:2, inp] - refpos, pos3[0:2, inp] - refpos) ) / 6.0)
  surf[inp] = (norm(crossp(pos2[0:2, inp] - refpos, pos3[0:2, inp] - refpos)) + $
               norm(crossp(pos1[0:2, inp] - pos0[0:2, inp], pos2[0:2, inp] - pos0[0:2, inp])) + $
               norm(crossp(pos1[0:2, inp] - pos0[0:2, inp], pos3[0:2, inp] - pos0[0:2, inp])) + $
               norm(crossp(pos1[0:2, inp] - pos2[0:2, inp], pos3[0:2, inp] - pos2[0:2, inp])) ) / 2.0
  leng[inp] = norm(pos1[0:2, inp] - pos0[0:2, inp]) + norm(pos2[0:2, inp] - pos0[0:2, inp]) + norm(pos3[0:2, inp] - pos0[0:2, inp]) + $
              norm(pos2[0:2, inp] - pos1[0:2, inp]) + norm(pos3[0:2, inp] - pos1[0:2, inp]) + norm(pos3[0:2, inp] - pos2[0:2, inp]) 
ENDFOR
idealvol = ((leng/6.0) ^ 3.0) * 0.117851 ; ----0.117851 = 2^0.5/12
qlfactor = volm  / idealvol
;stop

current[3, *] = sqrt(total(current[0: 2, *]^2.0, 1))


current = reform(current, 1, 4, np)
curlB   = current[0, 0:3, *] * miu3


;STOP
RETURN, current

END