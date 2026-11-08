(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_2 () (_ BitVec 1))
(assert
 true)
(assert
 (let (($x5118 (= i_2 (_ bv0 1))))
(not $x5118)))
(check-sat)
