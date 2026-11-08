(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_9 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x49 (and (distinct i_9 (_ bv1 8)) true)))
(not $x49)))
(check-sat)
