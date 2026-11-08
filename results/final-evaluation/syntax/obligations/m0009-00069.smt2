(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x5494 (bvsge s_7 (_ bv0 8))))
(not $x5494)))
(check-sat)
