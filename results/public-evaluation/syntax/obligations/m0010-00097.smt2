(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_6 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x738 (bvsle i_6 (_ bv0 8))))
(not $x738)))
(check-sat)
