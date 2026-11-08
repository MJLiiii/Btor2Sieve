(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x2500 (= i_7 (_ bv1 8))))
(not $x2500)))
(check-sat)
