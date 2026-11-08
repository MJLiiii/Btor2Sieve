(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_6 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x1329 (bvsle i_6 (_ bv0 8))))
(not $x1329)))
(check-sat)
