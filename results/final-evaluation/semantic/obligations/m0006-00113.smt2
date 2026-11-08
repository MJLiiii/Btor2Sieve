(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_3 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x544 (bvsge s_3 (_ bv0 4))))
(not $x544)))
(check-sat)
