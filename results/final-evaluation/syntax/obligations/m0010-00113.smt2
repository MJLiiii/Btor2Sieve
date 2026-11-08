(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x4048 (= i_7 (_ bv0 8))))
(not $x4048)))
(check-sat)
