(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_2 () (_ BitVec 1))
(assert
 true)
(assert
 (let (($x1234 (= i_2 (_ bv1 1))))
(not $x1234)))
(check-sat)
