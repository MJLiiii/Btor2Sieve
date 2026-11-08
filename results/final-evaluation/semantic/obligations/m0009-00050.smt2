(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_6 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x763 (bvule s_6 (_ bv1 4))))
(not $x763)))
(check-sat)
