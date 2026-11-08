(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_6 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x56 (bvsle i_6 (_ bv1 8))))
(not $x56)))
(check-sat)
