(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_2 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x3313 (= i_2 (_ bv0 4))))
(not $x3313)))
(check-sat)
