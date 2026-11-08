(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x3121 (and (distinct i_7 (_ bv127 8)) true)))
(not $x3121)))
(check-sat)
