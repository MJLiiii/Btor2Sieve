(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_9 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x198 (and (distinct i_9 (_ bv127 8)) true)))
(not $x198)))
(check-sat)
