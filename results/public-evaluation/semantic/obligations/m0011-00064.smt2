(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_2 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x64 (bvsle i_2 (_ bv15 4))))
(not $x64)))
(check-sat)
