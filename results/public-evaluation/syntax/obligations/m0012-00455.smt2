(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 true)
(assert
 (let (($x710 (= i_4 (_ bv0 3))))
(not $x710)))
(check-sat)
