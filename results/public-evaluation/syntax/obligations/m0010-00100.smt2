(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_6 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x583 (and (distinct i_6 (_ bv1 8)) true)))
(not $x583)))
(check-sat)
