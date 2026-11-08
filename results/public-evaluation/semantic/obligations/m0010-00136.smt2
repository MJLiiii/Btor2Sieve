(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x46 (= i_7 (_ bv127 8))))
(not $x46)))
(check-sat)
