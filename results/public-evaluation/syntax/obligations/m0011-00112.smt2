(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_6 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x560 (bvule s_6 (_ bv8 4))))
(not $x560)))
(check-sat)
