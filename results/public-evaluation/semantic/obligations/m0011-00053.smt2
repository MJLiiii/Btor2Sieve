(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_2 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x17 (bvsle i_2 (_ bv0 4))))
(not $x17)))
(check-sat)
