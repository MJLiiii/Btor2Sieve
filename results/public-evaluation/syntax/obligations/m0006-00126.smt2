(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_3 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x354 (bvule s_3 (_ bv8 4))))
(not $x354)))
(check-sat)
