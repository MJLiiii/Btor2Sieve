(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_8 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x53 (bvsle i_8 (_ bv15 4))))
(not $x53)))
(check-sat)
