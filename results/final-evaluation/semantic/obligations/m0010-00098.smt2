(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_6 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x535 (and (distinct i_6 (_ bv1 8)) true)))
(not $x535)))
(check-sat)
